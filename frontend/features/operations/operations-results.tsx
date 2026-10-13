"use client";

import { useState } from "react";
import { Pagination } from "@/components/pagination";
import { ConfirmationDialog } from "@/components/confirmation-dialog";
import { polygonBounds } from "@/lib/annotation-viewport";
import { readingLabelStatus } from "@/lib/review-status";
import { ReadingRegionAnnotator } from "@/components/reading-region-annotator";
import { useOperationsReview, filters, pageSize } from "./use-operations-review";

export function OperationsResults({ csrfToken, refreshKey = 0 }: { csrfToken: string; refreshKey?: number }) {
  const [focusImage, setFocusImage] = useState(false);
  const { confirmation, conflictId, reloadConflict, rows, selectedId, filter, counts, searchInput, setSearchInput, page, total, loading, busy, error, message, recognitionStatus, recognizingSelected, mode, setMode, integerDigits, setIntegerDigits, incomplete, setIncomplete, unsaved, inputRef, pauseRows, selected, draft, editable, selectedIndex, meterChanged, load, setSavedId, patchDraft, choose, changeFilter, changePage, saveAll, recognize, confirm, searchSubmit } = useOperationsReview(csrfToken, refreshKey);
  return <section className={`panel full-span operations-studio annotation-desk ${focusImage ? "studio-focus" : ""}`} aria-labelledby="studio-title">
    <ConfirmationDialog confirmation={confirmation} />
    <header className="studio-heading">
      <div><p className="eyebrow">Không gian gắn nhãn</p><h2 id="studio-title">Kiểm tra & gắn nhãn</h2></div>
      <div className="studio-heading-actions">
        <button className="secondary" type="button" aria-pressed={focusImage} onClick={() => setFocusImage((value) => !value)}>{focusImage ? "Hiện danh sách ảnh" : "Tập trung vào ảnh"}</button>
        <button className="secondary" type="button" onClick={() => { setSavedId(null); void load(); }} disabled={busy || loading || incomplete}>Làm mới</button>
      </div>
    </header>
    <div className="studio-filters" role="group" aria-label="Lọc trạng thái ảnh">
      {filters.map((item) => <button key={item.key} type="button" aria-pressed={filter === item.key} disabled={busy} onClick={() => changeFilter(item.key)}><span>{item.label}</span><strong>{counts[item.key]}</strong></button>)}
    </div>
    <p className="studio-filter-help">“Cần xử lý” là tổng các ảnh chưa gắn nhãn và đã gắn nhãn nhưng chưa xác nhận.</p>
    {pauseRows && <p className="muted" role="status">Tạm dừng tự cập nhật danh sách để giữ ảnh và thay đổi đang làm. Bộ đếm vẫn cập nhật; bấm Làm mới khi cần.</p>}
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
        {conflictId && conflictId === selectedId && <button type="button" className="secondary" disabled={busy} onClick={() => void reloadConflict()}>Tải bản mới nhất của ảnh này</button>}
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
            <div><dt>Chỉ số</dt><dd>{readingLabelStatus(selected.review_status, selected.final_meter_reading, draft.reading)}</dd></div>
          </dl>
          {editable && <div className="studio-save-actions">
            <button type="button" disabled={busy || incomplete} onClick={() => void saveAll(false)}>{busy ? "Đang lưu…" : mode === "meter" ? "Lưu vùng công tơ" : "Lưu nhãn chỉ số"}</button>
            <button type="button" className="secondary" disabled={busy} onClick={() => void saveAll(true)}>Lưu và ảnh tiếp →</button>
            <small>{mode === "meter" ? "Lưu riêng vùng công tơ, không yêu cầu chỉ số hay mã khách hàng." : "Lưu chỉ số và các vùng khoanh để huấn luyện."} Mã khách hàng và kỳ tháng chỉ được lưu khi xác nhận chính thức bên dưới.</small>
          </div>}
          <details className="studio-ocr"><summary>Gợi ý nhận diện OCR</summary><strong>{selected.meter_reading_ai ?? "Chưa đọc được"}</strong><p className="muted">Điểm tham khảo {Math.round(selected.final_confidence * 100)}% · Cần kiểm tra bằng mắt.</p>
            <button type="button" className="secondary" disabled={busy || selected.image_status === "REJECTED" || !selected.meter_reading_ai} onClick={() => patchDraft({ reading: selected.meter_reading_ai ?? "" })}>Dùng kết quả OCR</button>
          <label>Số ô nguyên (không tính ô đỏ)<select value={integerDigits} onChange={(event) => setIntegerDigits(Number(event.target.value))} disabled={busy}>{[4, 5, 6, 7, 8].map((n) => <option key={n} value={n}>{n} chữ số</option>)}</select></label>
          {editable && <button type="button" className="secondary" onClick={() => void recognize()} disabled={busy || recognizingSelected || incomplete || !draft.readingPolygon}>{recognizingSelected ? "OCR đang chạy trong nền…" : "Đọc lại vùng đã khoanh"}</button>}
          {recognitionStatus && <p className="muted" role="status">{recognitionStatus}</p>}
          </details>
          {selected.image_status !== "REJECTED" && <button className="secondary studio-reject" type="button" disabled={busy} onClick={() => void confirm("REJECT")}>Từ chối ảnh này</button>}
          {selected.image_status === "REJECTED" && <button type="button" disabled={busy} onClick={() => void confirm("REOPEN")}>Khôi phục về Cần xử lý</button>}
        </> : <p className="muted">Chọn ảnh bên trái để nhập và lưu chỉ số.</p>}
      </aside>
    </div>
    <div className="studio-pagination-bar"><Pagination pageIndex={page} totalPages={Math.max(1, Math.ceil(total / pageSize))} onPageChange={changePage} disabled={busy || loading} ariaLabel="Phân trang danh sách ảnh" itemSummary={`${total} ảnh`} /></div>
          {selected && draft && selected.image_status !== "REJECTED" && <details className="studio-official" key={selected.image_id} open={selected.image_status === "CONFIRMED" ? true : undefined}>
            <summary>Xác nhận chính thức · Khách hàng & kỳ ghi điện</summary>
            <p className="muted">Chỉ dùng khi đã biết khách hàng và kỳ ghi điện. Mọi thay đổi được ghi nhật ký.</p>
            <label>Mã khách hàng<input value={draft.customer} disabled={busy} onChange={(event) => patchDraft({ customer: event.target.value })} /></label>
            <label>Kỳ ghi điện<input type="month" value={draft.month} disabled={busy} onInput={(event) => patchDraft({ month: event.currentTarget.value })} onChange={(event) => patchDraft({ month: event.target.value })} /></label>
            <button type="button" disabled={busy} onClick={() => void confirm("CONFIRM")}>{selected.image_status === "CONFIRMED" ? "Lưu thay đổi chính thức" : "Xác nhận chỉ số chính thức"}</button>
          </details>}
  </section>;
}
