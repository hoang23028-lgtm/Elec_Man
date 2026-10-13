"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Pagination } from "@/components/pagination";
import { usePanelActive } from "@/components/section-tabs";
import { useLeaveGuard } from "@/hooks/use-leave-guard";
import { useLatestRequest } from "@/hooks/use-latest-request";
import { getTrainingData, saveTrainingData, type DatasetItem, type DatasetPage } from "@/services/administration";

const partitions: Record<string, string> = { UNASSIGNED: "Chưa phân tập", TRAIN: "Huấn luyện", VALIDATION: "Chọn trọng số", HOLDOUT: "Kiểm tra độc lập (khóa)" };
const initial = { group_key: "", partition: "UNASSIGNED", identity_verified: false, label_verified: false, notes: "" };

export function TrainingDataQuality({ csrfToken }: { csrfToken: string }) {
  const active = usePanelActive();
  const request = useLatestRequest();
  const [data, setData] = useState<DatasetPage | null>(null);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<DatasetItem | null>(null);
  const [form, setForm] = useState(initial);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  useLeaveGuard(dirty, busy, "xác minh dữ liệu huấn luyện");

  const load = useCallback(async () => {
    const token = request.begin();
    setLoading(true);
    try {
      const result = await getTrainingData(page * 12, search);
      if (request.isCurrent(token)) { setData(result); setError(null); }
    } catch (reason) {
      if (request.isCurrent(token)) setError(reason instanceof Error ? reason.message : "Không thể tải dữ liệu.");
    } finally { if (request.isCurrent(token)) setLoading(false); }
  }, [page, search, request]);
  useEffect(() => {
    if (!active) return;
    const timer = window.setTimeout(() => { void load(); }, 250);
    return () => { window.clearTimeout(timer); request.invalidate(); };
  }, [active, load, request]);
  useEffect(() => { if (error) errorRef.current?.focus(); }, [error]);

  function select(item: DatasetItem) {
    if (busy || dirty) return;
    setSelected(item);
    setForm({ group_key: item.annotation.group_key ?? "", partition: item.annotation.partition ?? "UNASSIGNED", identity_verified: item.annotation.identity_verified ?? false, label_verified: item.annotation.label_verified ?? false, notes: item.annotation.notes ?? "" });
    setError(null); setNotice(null);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || busy) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const annotation = await saveTrainingData(selected.image_id, { ...form, group_key: form.group_key.trim() || null, notes: form.notes.trim() || null, expected_revision: selected.annotation.revision ?? 0, expected_label_revision: selected.label_revision }, csrfToken);
      setSelected({ ...selected, annotation }); setDirty(false);
      await load();
      setNotice("Đã lưu xác minh/phân tập và nhật ký trước–sau. Nhãn số gốc không bị thay đổi.");
      window.dispatchEvent(new Event("training-data-changed"));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể lưu. Nội dung đang nhập được giữ lại."); }
    finally { setBusy(false); }
  }
  const locked = Boolean(selected?.annotation.holdout_locked_at);
  return <section className="panel full-span" aria-labelledby="dataset-title">
    <div className="section-heading"><div><p className="eyebrow">Chất lượng dữ liệu</p><h2 id="dataset-title">Xác minh nhãn và nhóm công tơ</h2><p className="muted">Một công tơ phải cùng một nhóm và cùng một phân tập, kể cả ảnh chụp nhiều tháng. Không biết mã khách hàng vẫn có thể dùng mã nhóm như CT001; chỉ xác minh khi biết chắc.</p></div><button type="button" className="secondary" disabled={busy || dirty || loading} onClick={() => void load()}>Làm mới</button></div>
    {error && <p ref={errorRef} tabIndex={-1} className="error" role="alert" id="dataset-error">{error}</p>}
    {notice && <p className="notice" role="status">{notice}</p>}
    <div className="metrics"><div><strong>{data?.summary.verified ?? "—"}</strong><span>Đã xác minh</span></div><div><strong>{data?.summary.train ?? "—"}</strong><span>Huấn luyện</span></div><div><strong>{data?.summary.validation ?? "—"}</strong><span>Chọn trọng số</span></div><div><strong>{data?.summary.holdout ?? "—"}</strong><span>Kiểm tra độc lập</span></div></div>
    <p className="read-only-note">Chưa xác minh định danh: {data?.summary.unverified_identity ?? "—"} · Nhãn thay đổi cần kiểm tra lại: {data?.summary.stale_labels ?? "—"}. Phân tập kiểm tra độc lập bị khóa ngay khi lưu, không được chuyển lại sang tập học.</p>
    {data?.summary.conflicts.map((message) => <p className="error" key={message}>{message}</p>)}
    <label htmlFor="dataset-search">Tìm ảnh, mã khách hàng hoặc nhóm công tơ</label><input id="dataset-search" value={search} disabled={dirty || busy} onChange={(event) => { setSearch(event.target.value); setPage(0); }} />
    <div className="dataset-workspace">
      <div><div className="table-wrap" aria-busy={loading}><table><thead><tr><th className="row-number">STT</th><th>Ảnh / nhãn số</th><th>Nhóm / phân tập</th><th>Cần kiểm tra</th><th>Thao tác</th></tr></thead><tbody>{data?.items.map((item, index) => <tr key={item.image_id}><td>{page * 12 + index + 1}</td><td>{item.filename}<small>{item.label ?? "Chưa có nhãn số"}</small></td><td>{item.annotation.group_key ?? "Chưa xác minh"}<small>{partitions[item.annotation.partition ?? "UNASSIGNED"]}</small></td><td>{item.issues.length ? item.issues.join("; ") : "Đủ điều kiện"}</td><td><button className="secondary" type="button" disabled={dirty || busy} onClick={() => select(item)}>Kiểm tra</button></td></tr>)}{!data?.items.length && <tr><td colSpan={5}>{loading ? "Đang tải…" : "Không có ảnh phù hợp."}</td></tr>}</tbody></table></div><Pagination pageIndex={page} totalPages={Math.ceil((data?.total ?? 0) / 12)} onPageChange={setPage} disabled={dirty || busy || loading} ariaLabel="Dữ liệu huấn luyện" itemSummary={`${data?.total ?? 0} ảnh`} /></div>
      {selected && <form className="dataset-editor" onSubmit={submit} aria-describedby={error ? "dataset-error" : undefined}>
        <h3>{selected.filename} · {selected.label ?? "Chưa có nhãn số"}</h3>
        {/* Same-origin, authenticated preview; no public storage URL. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/api/v1/images/${selected.image_id}/preview`} alt={`Ảnh kiểm tra nhãn ${selected.filename}`} className="dataset-preview" />
        <p className="muted">Kiểm tra ảnh và nhãn số gốc tại <a href="#operations">Vận hành</a> trước khi đánh dấu đã xác minh.</p>
        <fieldset disabled={busy} className="editor-fields" onChange={() => setDirty(true)}>
          <label htmlFor="dataset-group">Mã nhóm công tơ (không phải mã khách hàng OCR)</label><input id="dataset-group" value={form.group_key} maxLength={64} pattern="[A-Za-z0-9][A-Za-z0-9._-]{0,63}" required={form.partition !== "UNASSIGNED" || form.identity_verified} disabled={locked} onChange={(event) => setForm({ ...form, group_key: event.target.value })} />
          <label htmlFor="dataset-partition">Phân tập</label><select id="dataset-partition" value={form.partition} disabled={locked} onChange={(event) => setForm({ ...form, partition: event.target.value })}>{Object.entries(partitions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <label className="checkbox-label"><input type="checkbox" checked={form.identity_verified} onChange={(event) => setForm({ ...form, identity_verified: event.target.checked })} /> Tôi đã xác minh các ảnh cùng nhóm thuộc cùng công tơ</label>
          <label className="checkbox-label"><input type="checkbox" checked={form.label_verified} onChange={(event) => setForm({ ...form, label_verified: event.target.checked })} /> Tôi đã kiểm tra chuỗi số, vùng số và vùng công tơ</label>
          <label htmlFor="dataset-notes">Ghi chú</label><textarea id="dataset-notes" value={form.notes} maxLength={1000} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          <div className="inline-controls"><button type="submit">{busy ? "Đang lưu…" : "Lưu xác minh / phân tập"}</button><button className="secondary" type="button" onClick={() => { setSelected(null); setDirty(false); setError(null); }}>Đóng, bỏ nội dung chưa lưu</button></div>
        </fieldset>
      </form>}
    </div>
  </section>;
}
