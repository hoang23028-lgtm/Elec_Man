"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Pagination } from "@/components/pagination";
import { polygonBounds } from "@/lib/annotation-viewport";
import { ReadingRegionAnnotator } from "@/components/reading-region-annotator";
import { usePolling } from "@/hooks/use-polling";
import { useLeaveGuard } from "@/hooks/use-leave-guard";
import { getResultsPage, getRecognitionStatus, getResultStatusCounts, recognizeReading, reviewResult, saveTrainingLabel, saveMeterRegion, type Result, type ResultStatusCounts, type ReadingPolygon } from "@/services/results";

type Draft = { reading: string; customer: string; month: string; readingPolygon: ReadingPolygon | null; meterPolygon: ReadingPolygon | null };
type Filter = keyof ResultStatusCounts;
const filters: { key: Filter; label: string; status: string; review?: string }[] = [
  { key: "review_required", label: "Cần xử lý", status: "REVIEW_REQUIRED" },
  { key: "pending", label: "Chưa gắn nhãn", status: "REVIEW_REQUIRED", review: "PENDING" },
  { key: "labeled", label: "Đã gắn nhãn · chờ xác nhận", status: "REVIEW_REQUIRED", review: "LABELED" },
  { key: "confirmed", label: "Đã xác nhận", status: "CONFIRMED", review: "CONFIRMED" },
  { key: "rejected", label: "Đã từ chối", status: "REJECTED", review: "REJECTED" },
];
const emptyCounts: ResultStatusCounts = { review_required: 0, pending: 0, labeled: 0, confirmed: 0, rejected: 0 };
const pageSize = 12;
function initialDraft(row: Result): Draft {
  return { reading: row.final_meter_reading ?? row.meter_reading_ai ?? "", customer: row.final_customer_id ?? row.customer_id_ai ?? "", month: row.reading_month?.slice(0, 7) ?? "", readingPolygon: row.reading_polygon, meterPolygon: row.meter_polygon };
}

export function OperationsResults({ csrfToken, refreshKey = 0 }: { csrfToken: string; refreshKey?: number }) {
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
    try {
      const statusCounts = await getResultStatusCounts(search);
      if (alive.current) setCounts(statusCounts);
    } catch {
      // Danh sách chính vẫn hiển thị được; lần tải đầy đủ tiếp theo sẽ báo lỗi nếu cần.
    }
  }, [search]);
  useEffect(() => { void load(); }, [load, refreshKey]);
  usePolling(() => load(false), 8000, !busy && !savedId && !selectedId);
  usePolling(refreshCounts, 8000, !busy && !!selectedId);
  const selected = rows.find((row) => row.image_id === selectedId);
  const draft = selected ? drafts[selected.image_id] ?? initialDraft(selected) : null;
  const editable = selected?.image_status === "REVIEW_REQUIRED";
  const selectedIndex = rows.findIndex((row) => row.image_id === selectedId);
  const meterChanged = !!selected && !!draft && JSON.stringify(draft.meterPolygon) !== JSON.stringify(selected.meter_polygon);

  function syncDirty(row: Result, value: Draft) {
    if (JSON.stringify(initialDraft(row)) === JSON.stringify(value)) dirty.current.delete(row.image_id);
    else dirty.current.add(row.image_id);
    setUnsaved(new Set(dirty.current));
  }

  async function saveMeter() {
    if (!selected || !draft?.meterPolygon) return false;
    requestId.current += 1; setLoading(false); setBusy(true); setError(null); setMessage(null);
    try {
      const polygon = await saveMeterRegion(selected.image_id, csrfToken, draft.meterPolygon);
      const updated = { ...selected, meter_polygon: polygon };
      window.dispatchEvent(new Event("training-data-changed"));
      const updatedDraft = { ...draft, meterPolygon: polygon };
      setRows((current) => current.map((row) => row.image_id === selected.image_id ? updated : row));
      setDrafts((current) => ({ ...current, [selected.image_id]: updatedDraft }));
      syncDirty(updated, updatedDraft);
      setMessage("Đã lưu vùng toàn bộ công tơ vào cơ sở dữ liệu. Chỉ số và các nhãn khác không thay đổi.");
      return true;
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không lưu được vùng công tơ."); return false; }
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
      await saveTrainingLabel(selected.image_id, csrfToken, draft.reading.trim(), draft.readingPolygon, draft.meterPolygon);
      syncDirty({ ...selected, final_meter_reading: draft.reading.trim(), reading_polygon: draft.readingPolygon, meter_polygon: draft.meterPolygon ?? selected.meter_polygon }, { ...draft, reading: draft.reading.trim() });
      setSavedId(selected.image_id);
      // Keep the saved image visible until the user chooses the next one.
      setRows((current) => current.map((row) => row.image_id === selected.image_id ? { ...row, review_status: "LABELED", final_meter_reading: draft.reading.trim(), reading_polygon: draft.readingPolygon, meter_polygon: draft.meterPolygon ?? row.meter_polygon } : row));
      if (selected.review_status !== "LABELED") {
        setCounts((current) => ({
          ...current,
          pending: Math.max(0, current.pending - 1),
          labeled: current.labeled + 1,
        }));
      }
      setMessage("Đã lưu nhãn vào cơ sở dữ liệu. Bạn có thể chuyển sang ảnh tiếp theo.");
      setDrafts((current) => ({ ...current, [selected.image_id]: { ...draft, reading: draft.reading.trim() } }));
      window.dispatchEvent(new Event("training-data-changed"));
      return true;
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không lưu được nhãn."); return false; }
    finally { setBusy(false); }
  }
  async function saveAll(advance: boolean) {
    if (!selected || !draft || busy) return;
    if (incomplete) { setError("Chọn đủ 4 góc hoặc bấm Vẽ lại trước khi lưu."); return; }
    if ((selected.meter_polygon && !draft.meterPolygon) || (selected.reading_polygon && !draft.readingPolygon)) {
      setError("Bạn đang vẽ lại vùng. Hãy chọn đủ 4 góc trước khi lưu."); return;
    }
    if (!draft.readingPolygon && draft.reading !== initialDraft(selected).reading) {
      setError("Hãy khoanh vùng chỉ số để lưu số bạn vừa nhập."); return;
    }
    const savesLabel = !!draft.readingPolygon;
    const saved = savesLabel ? await saveLabel() : await saveMeter();
    if (!saved && !draft.meterPolygon && !draft.readingPolygon) setError("Chọn 4 góc vùng công tơ hoặc vùng chỉ số trước khi lưu.");
    if (saved && savesLabel && filter === "pending") {
      setSavedId(null);
      await load(false);
      setMessage("Đã lưu nhãn và chuyển ảnh sang nhóm Đã gắn nhãn · chờ xác nhận.");
      return;
    }
    if (saved && advance) {
      if (draft.customer !== initialDraft(selected).customer || draft.month !== initialDraft(selected).month) {
        setMessage("Đã lưu nhãn. Mã khách hàng hoặc kỳ tháng chưa được lưu chính thức; hãy xác nhận bên dưới trước khi chuyển ảnh.");
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
  async function confirm(action: "CONFIRM" | "REJECT") {
    if (!selected || !draft || busy) return;
    if (action === "CONFIRM" && (incomplete || (selected.meter_polygon && !draft.meterPolygon) || (selected.reading_polygon && !draft.readingPolygon))) {
      setError("Vùng đang vẽ dở. Hoàn thành đủ 4 góc trước khi xác nhận."); return;
    }
    if (action === "CONFIRM" && (!draft.customer.trim() || !draft.month || !/^[0-9]{4,8}$/.test(draft.reading.trim()))) {
      setError("Xác nhận chính thức cần mã khách hàng, kỳ tháng và chỉ số hợp lệ."); return;
    }
    if (action === "REJECT" && !window.confirm("Từ chối ảnh này? Quyết định sẽ được lưu vào nhật ký.")) return;
    requestId.current += 1; setLoading(false); setBusy(true); setError(null); setMessage(null);
    try {
      await reviewResult(selected.image_id, csrfToken, action, draft.customer.trim(), draft.reading.trim(), draft.readingPolygon, draft.month, draft.meterPolygon);
      dirty.current.delete(selected.image_id);
      setUnsaved(new Set(dirty.current));
      await load(false);
      setMessage(action === "CONFIRM" ? "Đã lưu chỉ số chính thức và nhật ký thay đổi." : "Đã từ chối ảnh và ghi nhật ký.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không lưu được kết quả."); }
    finally { setBusy(false); }
  }
  function searchSubmit(event: FormEvent) { event.preventDefault(); if (!canSwitch()) return; setSavedId(null); setSearch(searchInput.trim()); setPage(0); }

  return <section className="panel full-span operations-studio annotation-desk" aria-labelledby="studio-title">
    <header className="studio-heading">
      <div><p className="eyebrow">Không gian gắn nhãn</p><h2 id="studio-title">Kiểm tra & gắn nhãn</h2></div>
      <button className="secondary" type="button" onClick={() => void load()} disabled={busy || loading}>Làm mới</button>
    </header>
    <div className="studio-filters" role="group" aria-label="Lọc trạng thái ảnh">
      {filters.map((item) => <button key={item.key} type="button" aria-pressed={filter === item.key} disabled={busy} onClick={() => changeFilter(item.key)}><span>{item.label}</span><strong>{counts[item.key]}</strong></button>)}
    </div>
    <p className="studio-filter-help">“Cần xử lý” là tổng các ảnh chưa gắn nhãn và đã gắn nhãn nhưng chưa xác nhận.</p>
    <div className="studio-grid">
      <aside className="studio-queue" aria-label="Danh sách ảnh">
        <form onSubmit={searchSubmit}><label htmlFor="studio-search">Tìm ảnh hoặc mã khách hàng</label><div className="studio-search"><input id="studio-search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} disabled={busy} placeholder="Tên ảnh, mã, chỉ số…" /><button type="submit" className="secondary" disabled={busy}>Tìm</button></div></form>
        <p className="studio-count">{total} ảnh · Trang {page + 1}/{Math.max(1, Math.ceil(total / pageSize))}</p>
        <div className="studio-file-list" aria-busy={loading}>
          {rows.map((row, index) => <button type="button" className="studio-file" aria-pressed={selectedId === row.image_id} disabled={busy} key={row.image_id} onClick={() => choose(row.image_id)}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`/api/v1/images/${row.image_id}/thumbnail`} alt="" loading="lazy" />
            <span><strong>{page * pageSize + index + 1}. {row.original_filename}</strong><small>{row.review_status === "LABELED" ? "Đã lưu nhãn" : row.review_status === "CONFIRMED" ? "Đã xác nhận" : row.review_status === "REJECTED" ? "Đã từ chối" : "Chưa gắn nhãn"}{unsaved.has(row.image_id) ? " · Có thay đổi chưa lưu" : ""}</small></span>
          </button>)}
          {!rows.length && <p className="empty-state">{loading ? "Đang tải ảnh…" : "Không có ảnh trong bộ lọc này."}</p>}
        </div>
      </aside>
      <section className="studio-viewer" aria-label="Ảnh và vùng chỉ số">
        {selected && draft ? <>
          <div className="studio-image-title"><strong>{selected.original_filename}</strong><span className="muted">{selectedIndex + 1} / {rows.length} ảnh trên trang</span></div>
          <ReadingRegionAnnotator compact focusBox={polygonBounds(draft.meterPolygon) ?? selected.ai_meter_bbox} focusSource={draft.meterPolygon ? "Đang ưu tiên vùng công tơ bạn khoanh." : "Vùng công tơ AI đề xuất — cần kiểm tra lại."} onIncompleteChange={setIncomplete} toolbar={<div className="studio-region-tabs" role="group" aria-label="Vùng cần khoanh">
            <button type="button" aria-pressed={mode === "meter"} disabled={busy || incomplete} onClick={() => setMode("meter")}>Vùng công tơ</button>
            <button type="button" aria-pressed={mode === "reading"} disabled={busy || incomplete} onClick={() => setMode("reading")}>Vùng chỉ số</button>
          </div>} key={`${selected.image_id}-${mode}`} imageUrl={`/api/v1/images/${selected.image_id}/preview`} imageAlt={`Ảnh công tơ ${selected.original_filename}`} annotationKind={mode} value={mode === "reading" ? draft.readingPolygon : draft.meterPolygon} automaticValue={mode === "reading" ? selected.ai_reading_bbox : selected.ai_meter_bbox} onChange={(value) => patchDraft(mode === "reading" ? { readingPolygon: value } : { meterPolygon: value })} recognizing={busy || !editable} canRecognize={editable} />
        </> : <div className="studio-placeholder"><h3>Chọn một ảnh để bắt đầu</h3><p>Ảnh và công cụ khoanh vùng sẽ hiện tại đây.</p></div>}
      </section>
      <aside className="studio-inspector" aria-label="Chỉ số và lưu kết quả">
        {error && <p className="error" role="alert">{error}</p>}
        {message && <p className="notice" role="status">{message}</p>}
        {selected && draft ? <>
          <div className="studio-label-form">
            <p className="eyebrow">Nhãn của ảnh</p>
            <label htmlFor="verified-reading">Chỉ số đúng · kWh</label>
            <input id="verified-reading" ref={inputRef} className="studio-reading-input" inputMode="numeric" value={draft.reading} onChange={(event) => patchDraft({ reading: event.target.value })} disabled={busy || selected.image_status === "REJECTED"} aria-describedby="label-help" />
            <p id="label-help" className="muted">Giữ số 0 đầu, bỏ ô đỏ cuối.</p>
          </div>
          <dl className="studio-label-status">
            <div><dt>Vùng công tơ</dt><dd>{meterChanged ? "Chưa lưu" : selected.meter_polygon ? "Đã lưu" : "Chưa khoanh"}</dd></div>
            <div><dt>Vùng chỉ số</dt><dd>{JSON.stringify(draft.readingPolygon) !== JSON.stringify(selected.reading_polygon) ? "Chưa lưu" : selected.reading_polygon ? "Đã lưu" : "Chưa khoanh"}</dd></div>
            <div><dt>Chỉ số</dt><dd>{draft.reading !== (selected.final_meter_reading ?? "") ? "Chưa lưu nhãn" : selected.final_meter_reading ? "Đã lưu" : "Chưa nhập"}</dd></div>
          </dl>
          {editable && <div className="studio-save-actions">
            <button type="button" disabled={busy} onClick={() => void saveAll(false)}>{busy ? "Đang lưu…" : "Lưu nhãn"}</button>
            <button type="button" className="secondary" disabled={busy} onClick={() => void saveAll(true)}>Lưu và ảnh tiếp →</button>
            <small>Lưu chỉ số và các vùng khoanh để huấn luyện. Mã khách hàng và kỳ tháng chỉ được lưu khi xác nhận chính thức bên dưới.</small>
          </div>}
          <details className="studio-ocr"><summary>Gợi ý nhận diện OCR</summary><strong>{selected.meter_reading_ai ?? "Chưa đọc được"}</strong><p className="muted">Điểm tham khảo {Math.round(selected.final_confidence * 100)}% · Cần kiểm tra bằng mắt.</p>
            <button type="button" className="secondary" disabled={busy || selected.image_status === "REJECTED" || !selected.meter_reading_ai} onClick={() => patchDraft({ reading: selected.meter_reading_ai ?? "" })}>Dùng kết quả OCR</button>
          <label>Số ô nguyên (không tính ô đỏ)<select value={integerDigits} onChange={(event) => setIntegerDigits(Number(event.target.value))} disabled={busy}>{[4, 5, 6, 7, 8].map((n) => <option key={n} value={n}>{n} chữ số</option>)}</select></label>
          {editable && <button type="button" className="secondary" onClick={() => void recognize()} disabled={busy || recognizingSelected || incomplete || !draft.readingPolygon}>{recognizingSelected ? "OCR đang chạy trong nền…" : "Đọc lại vùng đã khoanh"}</button>}
          {recognitionStatus && <p className="muted" role="status">{recognitionStatus}</p>}
          </details>
          {editable && <button className="secondary studio-reject" type="button" disabled={busy} onClick={() => void confirm("REJECT")}>Từ chối ảnh này</button>}
        </> : <p className="muted">Chọn ảnh bên trái để nhập và lưu chỉ số.</p>}
      </aside>
    </div>
    <div className="studio-pagination-bar"><Pagination pageIndex={page} totalPages={Math.max(1, Math.ceil(total / pageSize))} onPageChange={changePage} disabled={busy || loading} ariaLabel="Phân trang danh sách ảnh" itemSummary={`${total} ảnh`} /></div>
          {selected && draft && selected.image_status !== "REJECTED" && <details className="studio-official" key={selected.image_id} open={selected.image_status === "CONFIRMED" ? true : undefined}>
            <summary>2 · Xác nhận dữ liệu chính thức</summary>
            <p className="muted">Chỉ dùng khi đã biết khách hàng và kỳ ghi điện. Mọi thay đổi được ghi nhật ký.</p>
            <label>Mã khách hàng<input value={draft.customer} disabled={busy} onChange={(event) => patchDraft({ customer: event.target.value })} /></label>
            <label>Kỳ ghi điện<input type="month" value={draft.month} disabled={busy} onChange={(event) => patchDraft({ month: event.target.value })} /></label>
            <button type="button" disabled={busy} onClick={() => void confirm("CONFIRM")}>{selected.image_status === "CONFIRMED" ? "Lưu thay đổi chính thức" : "Xác nhận chỉ số chính thức"}</button>
          </details>}
  </section>;
}
