"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { usePolling } from "@/hooks/use-polling";
import { useLeaveGuard } from "@/hooks/use-leave-guard";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { ApiError } from "@/services/http";
import { getResultsPage, getRecognitionStatus, getResultStatusCounts, recognizeReading, reviewResult, saveTrainingLabel, saveMeterRegion, type Result, type ResultStatusCounts, type ReadingPolygon } from "@/services/results";

type Draft = { revision: number; reading: string; customer: string; month: string; readingPolygon: ReadingPolygon | null; meterPolygon: ReadingPolygon | null };
type Filter = keyof ResultStatusCounts;
export const filters: { key: Filter; label: string; status: string; review?: string }[] = [
  { key: "review_required", label: "Cần xử lý", status: "REVIEW_REQUIRED" },
  { key: "pending", label: "Chưa gắn nhãn", status: "REVIEW_REQUIRED", review: "PENDING" },
  { key: "labeled", label: "Đã gắn nhãn · chờ xác nhận", status: "REVIEW_REQUIRED", review: "LABELED" },
  { key: "confirmed", label: "Đã xác nhận", status: "CONFIRMED", review: "CONFIRMED" },
  { key: "rejected", label: "Đã từ chối", status: "REJECTED", review: "REJECTED" },
];
const emptyCounts: ResultStatusCounts = { review_required: 0, pending: 0, labeled: 0, confirmed: 0, rejected: 0 };
export const pageSize = 12;
function initialDraft(row: Result): Draft {
  return { revision: row.revision, reading: row.final_meter_reading ?? row.meter_reading_ai ?? "", customer: row.final_customer_id ?? row.customer_id_ai ?? "", month: row.reading_month?.slice(0, 7) ?? "", readingPolygon: row.reading_polygon, meterPolygon: row.meter_polygon };
}


export function useOperationsReview(csrfToken: string, refreshKey: number) {
  const confirmation = useConfirmationDialog();
  const reviewing = useRef(false);
  const [rows, setRows] = useState<Result[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [filter, setFilter] = useState<Filter>("review_required");
  const [counts, setCounts] = useState<ResultStatusCounts>(emptyCounts);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [conflictId, setConflictId] = useState<string | null>(null);
  const [recognitionStatuses, setRecognitionStatuses] = useState<Record<string, string>>({});
  const [recognizingIds, setRecognizingIds] = useState<Set<string>>(new Set());
  const recognitionTasks = useRef(new Set<string>());
  const recognitionStatus = selectedId ? recognitionStatuses[selectedId] : null;
  const recognizingSelected = !!selectedId && recognizingIds.has(selectedId);
  const [mode, setMode] = useState<"reading" | "meter">("reading");
  const [integerDigits, setIntegerDigits] = useState(5);
  const [incomplete, setIncomplete] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const requestId = useRef(0);
  const alive = useRef(true);
  const dirty = useRef(new Set<string>());
  const [unsaved, setUnsaved] = useState<Set<string>>(new Set());
  const inputRef = useRef<HTMLInputElement>(null);
  useLeaveGuard(unsaved.size > 0 || incomplete, busy, "lưu nhãn / dữ liệu Vận hành");
  useEffect(() => { alive.current = true; return () => { alive.current = false; requestId.current += 1; }; }, []);
  const load = useCallback(async (foreground = true) => {
    const id = ++requestId.current;
    if (foreground) setLoading(true);
    const item = filters.find((entry) => entry.key === filter)!;
    try {
      const [result, statusCounts] = await Promise.all([
        getResultsPage({ offset: page * pageSize, limit: pageSize, imageStatus: item.status, reviewStatus: item.review, search }),
        getResultStatusCounts(search),
      ]);
      if (!alive.current || id !== requestId.current) return;
      if (!foreground && dirty.current.size > 0) { setCounts(statusCounts); return; }
      if (!result.items.length && page > 0) { setPage(Math.max(0, Math.ceil(result.total / pageSize) - 1)); return; }
      setRows(result.items); setTotal(result.total); setCounts(statusCounts); setError(null);
      setSelectedId((current) => result.items.some((row) => row.image_id === current) ? current : result.items[0]?.image_id ?? null);
      setDrafts((current) => {
        const next = { ...current };
        for (const row of result.items) if (!dirty.current.has(row.image_id)) next[row.image_id] = initialDraft(row);
        return next;
      });
    } catch (reason) { if (alive.current && id === requestId.current) setError(reason instanceof Error ? reason.message : "Không tải được danh sách ảnh."); }
    finally { if (alive.current && id === requestId.current) setLoading(false); }
  }, [filter, page, search]);
  const refreshCounts = useCallback(async () => {
    const version = requestId.current;
    try {
      const statusCounts = await getResultStatusCounts(search);
      if (alive.current && version === requestId.current) setCounts(statusCounts);
    } catch {
      // Danh sách chính vẫn hiển thị được; lần tải đầy đủ tiếp theo sẽ báo lỗi nếu cần.
    }
  }, [search]);
  useEffect(() => { void load(); }, [load, refreshKey]);
  const pauseRows = !!savedId || unsaved.size > 0 || incomplete;
  usePolling(() => load(false), 8000, !busy && !pauseRows);
  usePolling(refreshCounts, 8000, !busy && pauseRows);
  const selected = rows.find((row) => row.image_id === selectedId);
  const draft = selected ? drafts[selected.image_id] ?? initialDraft(selected) : null;
  const editable = selected?.image_status === "REVIEW_REQUIRED";
  const selectedIndex = rows.findIndex((row) => row.image_id === selectedId);
  const meterChanged = !!selected && !!draft && JSON.stringify(draft.meterPolygon) !== JSON.stringify(selected.meter_polygon);

  function handleSaveError(reason: unknown, imageId: string, fallback: string) {
    if (reason instanceof ApiError && reason.status === 412) setConflictId(imageId);
    setError(reason instanceof Error ? reason.message : fallback);
  }

  async function reloadConflict() {
    if (!selected || busy || reviewing.current) return;
    reviewing.current = true;
    setBusy(true);
    try {
      if (!await confirmation.ask({
        title: `Tải lại ${selected.original_filename}?`,
        description: "Bản nháp của ảnh này sẽ bị bỏ để tải bản mới nhất. Các bản nháp khác vẫn được giữ.",
        confirmLabel: "Bỏ bản nháp và tải lại",
        danger: true,
      }) || !alive.current) return;
      dirty.current.delete(selected.image_id);
      setUnsaved(new Set(dirty.current));
      setConflictId(null);
      setSavedId(null);
      setDrafts((current) => { const next = { ...current }; delete next[selected.image_id]; return next; });
      await load();
    } finally { reviewing.current = false; if (alive.current) setBusy(false); }
  }

  function syncDirty(row: Result, value: Draft) {
    if (JSON.stringify(initialDraft(row)) === JSON.stringify(value)) dirty.current.delete(row.image_id);
    else dirty.current.add(row.image_id);
    setUnsaved(new Set(dirty.current));
  }

  async function saveMeter() {
    if (!selected || !draft?.meterPolygon) return false;
    requestId.current += 1; setLoading(false); setBusy(true); setError(null); setMessage(null);
    try {
      const result = await saveMeterRegion(selected.image_id, csrfToken, draft.meterPolygon, draft.revision);
      const polygon = result.meter_polygon;
      const updated = { ...selected, revision: result.revision, meter_polygon: polygon };
      window.dispatchEvent(new Event("training-data-changed"));
      const updatedDraft = { ...draft, revision: result.revision, meterPolygon: polygon };
      setRows((current) => current.map((row) => row.image_id === selected.image_id ? updated : row));
      setDrafts((current) => ({ ...current, [selected.image_id]: updatedDraft }));
      syncDirty(updated, updatedDraft);
      setMessage("Đã lưu vùng toàn bộ công tơ vào cơ sở dữ liệu. Chỉ số và các nhãn khác không thay đổi.");
      return true;
    } catch (reason) { handleSaveError(reason, selected.image_id, "Không lưu được vùng công tơ."); return false; }
    finally { setBusy(false); }
  }

  function patchDraft(patch: Partial<Draft>) {
    if (!selected || !draft || busy) return;
    syncDirty(selected, { ...draft, ...patch });
    setDrafts((current) => ({ ...current, [selected.image_id]: { ...draft, ...patch } }));
    setMessage(null);
  }
  function canSwitch() {
    if (!incomplete) return true;
    setError("Bạn đang chọn dở các góc. Hoàn thành 4 điểm hoặc bấm Vẽ lại trước khi đổi ảnh.");
    return false;
  }
  function choose(id: string) { if (!canSwitch()) return; setSavedId(null); setSelectedId(id); setMode("reading"); setError(null); setMessage(null); }
  function changeFilter(value: Filter) { if (value === filter || !canSwitch()) return; requestId.current += 1; setSavedId(null); setFilter(value); setPage(0); setRows([]); setSelectedId(null); setError(null); setMessage(null); }
  function nextImage() {
    if (selectedIndex + 1 < rows.length) choose(rows[selectedIndex + 1].image_id);
    else if ((page + 1) * pageSize < total) { requestId.current += 1; setLoading(true); setSavedId(null); setRows([]); setSelectedId(null); setPage(page + 1); }
    else setMessage("Bạn đã ở ảnh cuối danh sách này.");
  }
  function changePage(next: number) {
    if (!canSwitch() || next === page) return;
    requestId.current += 1;
    setSavedId(null); setSelectedId(null); setRows([]); setLoading(true); setPage(next);
  }
  async function saveLabel() {
    if (!selected || !draft) return false;
    if (!draft.readingPolygon || !/^[0-9]{4,8}$/.test(draft.reading.trim())) {
      setError("Khoanh đủ 4 góc dãy số và nhập chỉ số đúng gồm 4–8 chữ số."); inputRef.current?.focus(); return false;
    }
    requestId.current += 1; setLoading(false); setBusy(true); setError(null); setMessage(null);
    try {
      const saved = await saveTrainingLabel(selected.image_id, csrfToken, draft.reading.trim(), draft.readingPolygon, draft.meterPolygon, draft.revision);
      syncDirty({ ...selected, revision: saved.revision, final_meter_reading: draft.reading.trim(), reading_polygon: draft.readingPolygon, meter_polygon: draft.meterPolygon ?? selected.meter_polygon }, { ...draft, revision: saved.revision, reading: draft.reading.trim() });
      setSavedId(selected.image_id);
      // Keep the saved image visible until the user chooses the next one.
      setRows((current) => current.map((row) => row.image_id === selected.image_id ? { ...row, revision: saved.revision, review_status: "LABELED", final_meter_reading: draft.reading.trim(), reading_polygon: draft.readingPolygon, meter_polygon: draft.meterPolygon ?? row.meter_polygon } : row));
      if (selected.review_status !== "LABELED") {
        setCounts((current) => ({
          ...current,
          pending: Math.max(0, current.pending - 1),
          labeled: current.labeled + 1,
        }));
      }
      setMessage("Đã lưu nhãn vào cơ sở dữ liệu. Bạn có thể chuyển sang ảnh tiếp theo.");
      setDrafts((current) => ({ ...current, [selected.image_id]: { ...draft, revision: saved.revision, reading: draft.reading.trim() } }));
      window.dispatchEvent(new Event("training-data-changed"));
      return true;
    } catch (reason) { handleSaveError(reason, selected.image_id, "Không lưu được nhãn."); return false; }
    finally { setBusy(false); }
  }
  async function saveAll(advance: boolean) {
    if (!selected || !draft || busy) return;
    if (incomplete) { setError("Chọn đủ 4 góc hoặc bấm Vẽ lại trước khi lưu."); return; }
    if ((mode === "meter" && !draft.meterPolygon) || (mode === "reading" && selected.reading_polygon && !draft.readingPolygon)) {
      setError("Bạn đang vẽ lại vùng. Hãy chọn đủ 4 góc trước khi lưu."); return;
    }
    if (mode === "reading" && !draft.readingPolygon && draft.reading !== initialDraft(selected).reading) {
      setError("Hãy khoanh vùng chỉ số để lưu số bạn vừa nhập."); return;
    }
    const savesLabel = mode === "reading";
    const saved = savesLabel ? await saveLabel() : await saveMeter();
    if (!saved && !draft.meterPolygon && !draft.readingPolygon) setError("Chọn 4 góc vùng công tơ hoặc vùng chỉ số trước khi lưu.");
    if (saved && advance) {
      if (dirty.current.has(selected.image_id)) {
        setMessage("Đã lưu vùng hoặc nhãn đã chọn. Ảnh vẫn còn thay đổi chưa lưu; hãy lưu phần còn lại trước khi chuyển ảnh.");
      } else if (savesLabel && filter === "pending") {
        setSavedId(null);
        await load(false);
        setMessage("Đã lưu nhãn và chuyển ảnh sang nhóm Đã gắn nhãn · chờ xác nhận.");
      } else nextImage();
    }
  }
  async function recognize() {
    if (!selected || !draft?.readingPolygon || incomplete) { setError("Hãy khoanh đủ 4 góc dãy số trước."); return; }
    const imageId = selected.image_id;
    if (recognitionTasks.current.has(imageId)) return;
    recognitionTasks.current.add(imageId);
    setRecognizingIds(new Set(recognitionTasks.current));
    const status = (text: string) => { if (alive.current) setRecognitionStatuses((current) => ({ ...current, [imageId]: text })); };
    requestId.current += 1; setLoading(false); setBusy(true); setError(null); setMessage(null); status("Đang gửi vùng ảnh…");
    let submitted = false;
    try {
      await recognizeReading(imageId, csrfToken, draft.readingPolygon, integerDigits);
      submitted = true;
      if (alive.current) setBusy(false);
      for (let attempt = 0; attempt < 240 && alive.current; attempt++) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        if (!alive.current) return;
        const result = await getRecognitionStatus(imageId);
        if (!alive.current) return;
        if (result.status === "FAILED") throw new Error(result.error_message ?? "Nhận diện thất bại.");
        status(result.status === "PENDING" ? "Đang chờ worker. Bạn có thể tiếp tục gắn nhãn hoặc đổi ảnh." : "Đang đọc dãy số trong nền…");
        if (result.status === "COMPLETED") {
          setRows((current) => current.map((row) => row.image_id === imageId ? { ...row, meter_reading_ai: result.meter_reading_ai } : row));
          status(result.meter_reading_ai ? "OCR đã lưu. Kiểm tra rồi chọn Dùng kết quả OCR nếu đúng; không ghi đè nhãn thủ công." : "Không đọc được. Bạn có thể nhập chỉ số thủ công và lưu nhãn.");
          return;
        }
      }
      throw new Error("Đã hết thời gian chờ; tác vụ vẫn chạy trong nền. Bấm Làm mới để xem kết quả.");
    } catch (reason) { status(reason instanceof Error ? reason.message : "Không nhận diện được."); }
    finally {
      recognitionTasks.current.delete(imageId);
      if (alive.current && !submitted) setBusy(false);
      if (alive.current) setRecognizingIds(new Set(recognitionTasks.current));
    }
  }
  async function confirm(action: "CONFIRM" | "REJECT" | "REOPEN") {
    if (!selected || !draft || busy || reviewing.current) return;
    if (action === "CONFIRM" && (incomplete || (selected.meter_polygon && !draft.meterPolygon) || (selected.reading_polygon && !draft.readingPolygon))) {
      setError("Vùng đang vẽ dở. Hoàn thành đủ 4 góc trước khi xác nhận."); return;
    }
    if (action === "CONFIRM" && (!draft.customer.trim() || !draft.month || !/^[0-9]{4,8}$/.test(draft.reading.trim()))) {
      setError("Xác nhận chính thức cần mã khách hàng, kỳ tháng và chỉ số hợp lệ."); return;
    }
    reviewing.current = true;
    requestId.current += 1; setLoading(false); setBusy(true);
    try {
      if (action === "REJECT" && (!await confirmation.ask({
        title: `Từ chối ${selected.original_filename}?`,
        description: selected.image_status === "CONFIRMED"
          ? "Ảnh đã xác nhận: chỉ số sẽ được gỡ khỏi dữ liệu chính thức và báo cáo tháng. Nhãn đã lưu vẫn được giữ; quyết định được ghi nhật ký."
          : "Bản nháp chưa lưu sẽ không được lưu. Nhãn đã lưu vẫn được giữ; quyết định được ghi nhật ký.",
        confirmLabel: "Từ chối ảnh",
        danger: true,
      }) || !alive.current)) return;
      setError(null); setMessage(null);
      await reviewResult(selected.image_id, csrfToken, action, draft.customer.trim(), draft.reading.trim(), draft.readingPolygon, draft.month, draft.meterPolygon, draft.revision);
      window.dispatchEvent(new Event("confirmed-data-changed"));
      window.dispatchEvent(new Event("training-data-changed"));
      dirty.current.delete(selected.image_id);
      setSavedId(null);
      setUnsaved(new Set(dirty.current));
      await load(false);
      setMessage(action === "CONFIRM" ? "Đã lưu chỉ số chính thức và nhật ký thay đổi." : action === "REOPEN" ? "Đã khôi phục ảnh về Cần xử lý. Các nhãn đã lưu được giữ nguyên." : "Đã từ chối ảnh và ghi nhật ký.");
    } catch (reason) { handleSaveError(reason, selected.image_id, "Không lưu được kết quả."); }
    finally { reviewing.current = false; if (alive.current) setBusy(false); }
  }
  function searchSubmit(event: FormEvent) { event.preventDefault(); if (!canSwitch()) return; setSavedId(null); setSearch(searchInput.trim()); setPage(0); }

  return { confirmation, conflictId, reloadConflict, rows, selectedId, filter, counts, searchInput, setSearchInput, page, total, loading, busy, error, message, recognitionStatus, recognizingSelected, mode, setMode, integerDigits, setIntegerDigits, incomplete, setIncomplete, unsaved, inputRef, pauseRows, selected, draft, editable, selectedIndex, meterChanged, load, setSavedId, patchDraft, choose, changeFilter, changePage, saveAll, recognize, confirm, searchSubmit };
}
