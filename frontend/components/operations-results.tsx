"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { Pagination } from "@/components/pagination";
import { ReadingRegionAnnotator } from "@/components/reading-region-annotator";
import {
  getRecognitionStatus,
  getResultsPage,
  recognizeReading,
  reviewResult,
  type ReadingBoundingBox,
  type Result,
} from "@/services/results";
import { usePolling } from "@/hooks/use-polling";

type Draft = {
  customer: string;
  reading: string;
  readingBbox: ReadingBoundingBox | null;
};
type Props = { csrfToken: string; refreshKey?: number };
type ImagePreview = {
  imageId: string;
  filename: string;
  automaticBbox: ReadingBoundingBox | null;
  canRecognize: boolean;
};

const pageSize = 12;
const recognitionPollMilliseconds = 1000;
const recognitionPollAttempts = 120;

function bboxStyle(bbox: ReadingBoundingBox) {
  return {
    left: `${bbox.x * 100}%`,
    top: `${bbox.y * 100}%`,
    width: `${bbox.width * 100}%`,
    height: `${bbox.height * 100}%`,
  };
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function initialDraft(row: Result): Draft {
  return {
    customer: row.final_customer_id ?? row.customer_id_ai ?? "",
    reading: row.final_meter_reading ?? row.meter_reading_ai ?? "",
    readingBbox: row.reading_bbox,
  };
}

function confidenceLabel(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function OperationsResults({ csrfToken, refreshKey = 0 }: Props) {
  const [pending, setPending] = useState<Result[]>([]);
  const [confirmed, setConfirmed] = useState<Result[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [confirmedTotal, setConfirmedTotal] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [pendingPage, setPendingPage] = useState(0);
  const [confirmedPage, setConfirmedPage] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<ImagePreview | null>(null);
  const [recognizingId, setRecognizingId] = useState<string | null>(null);
  const [recognitionStatus, setRecognitionStatus] = useState<string | null>(null);
  const previewDialogRef = useRef<HTMLDialogElement>(null);
  const previewTriggerRef = useRef<HTMLButtonElement | null>(null);

  const load = useCallback(
    async (showLoading = true) => {
      if (showLoading) setLoading(true);
      try {
        const [nextPending, nextConfirmed] = await Promise.all([
          getResultsPage({
            imageStatus: "REVIEW_REQUIRED",
            offset: pendingPage * pageSize,
            limit: pageSize,
            search,
          }),
          getResultsPage({
            imageStatus: "CONFIRMED",
            offset: confirmedPage * pageSize,
            limit: pageSize,
            search,
          }),
        ]);
        setPending(nextPending.items);
        setConfirmed(nextConfirmed.items);
        setPendingTotal(nextPending.total);
        setConfirmedTotal(nextConfirmed.total);
        setDrafts((current) => {
          const next = { ...current };
          for (const row of [...nextPending.items, ...nextConfirmed.items]) {
            if (!next[row.image_id]) next[row.image_id] = initialDraft(row);
          }
          return next;
        });
        setError(null);
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Không thể tải dữ liệu vận hành.",
        );
      } finally {
        if (showLoading) setLoading(false);
      }
    },
    [confirmedPage, pendingPage, search],
  );

  useEffect(() => {
    void load();
  }, [load, refreshKey]);
  usePolling(() => load(false), 8000);

  useEffect(() => {
    const dialog = previewDialogRef.current;
    if (imagePreview && dialog && !dialog.open) dialog.showModal();
  }, [imagePreview]);

  function openImagePreview(row: Result, trigger: HTMLButtonElement) {
    previewTriggerRef.current = trigger;
    setRecognitionStatus(null);
    setImagePreview({
      imageId: row.image_id,
      filename: row.original_filename,
      automaticBbox: row.ai_reading_bbox,
      canRecognize: row.image_status === "REVIEW_REQUIRED",
    });
  }

  function closeImagePreview() {
    previewDialogRef.current?.close();
  }

  function finishImagePreview() {
    setImagePreview(null);
    window.requestAnimationFrame(() => {
      if (previewTriggerRef.current?.isConnected) previewTriggerRef.current.focus();
    });
  }

  function updateDraft(id: string, field: "customer" | "reading", value: string) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...(current[id] ?? { customer: "", reading: "", readingBbox: null }), [field]: value },
    }));
  }

  function updateReadingBbox(id: string, value: ReadingBoundingBox | null) {
    setDrafts((current) => ({
      ...current,
      [id]: {
        ...(current[id] ?? { customer: "", reading: "", readingBbox: null }),
        readingBbox: value,
      },
    }));
  }

  async function recognizeSelectedReading() {
    if (!imagePreview) return;
    const draft = drafts[imagePreview.imageId];
    if (!draft?.readingBbox) {
      setRecognitionStatus("Hãy khoanh vùng chỉ số trước khi nhận diện.");
      return;
    }
    setRecognizingId(imagePreview.imageId);
    setRecognitionStatus("Đã gửi yêu cầu. Hệ thống đang xác định chỉ số trong vùng màu đỏ…");
    setError(null);
    try {
      await recognizeReading(imagePreview.imageId, csrfToken, draft.readingBbox);
      for (let attempt = 0; attempt < recognitionPollAttempts; attempt += 1) {
        await wait(recognitionPollMilliseconds);
        const status = await getRecognitionStatus(imagePreview.imageId);
        if (status.status === "FAILED") {
          throw new Error(status.error_message ?? "Không thể nhận diện vùng chỉ số.");
        }
        if (status.status === "COMPLETED") {
          setDrafts((current) => ({
            ...current,
            [imagePreview.imageId]: {
              ...(current[imagePreview.imageId] ?? draft),
              reading: status.meter_reading_ai ?? "",
            },
          }));
          setRecognitionStatus(
            status.meter_reading_ai
              ? `Đã nhận diện: ${status.meter_reading_ai} kWh. Kết quả vẫn chờ bạn xác nhận.`
              : "Không đọc được chỉ số trong vùng đã chọn. Hãy điều chỉnh vùng và thử lại.",
          );
          setMessage("Đã xác định lại chỉ số; kết quả vẫn nằm trong danh sách Cần xử lý.");
          await load(false);
          return;
        }
      }
      throw new Error("Quá thời gian chờ nhận diện. Tác vụ vẫn tiếp tục chạy trong nền.");
    } catch (reason) {
      const detail = reason instanceof Error ? reason.message : "Không thể xác định chỉ số.";
      setRecognitionStatus(detail);
      setError(detail);
    } finally {
      setRecognizingId(null);
    }
  }

  async function submitReview(row: Result, action: "CONFIRM" | "REJECT") {
    const draft = drafts[row.image_id] ?? initialDraft(row);
    setBusyId(row.image_id);
    setError(null);
    setMessage(null);
    try {
      await reviewResult(
        row.image_id,
        csrfToken,
        action,
        draft.customer.trim(),
        draft.reading.trim(),
        draft.readingBbox,
      );
      setMessage(
        action === "CONFIRM"
          ? "Đã xác nhận kết quả và lưu nhật ký thay đổi."
          : "Đã từ chối kết quả và lưu vào nhật ký.",
      );
      setDrafts((current) => {
        const next = { ...current };
        delete next[row.image_id];
        return next;
      });
      await load(false);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể lưu kết quả.",
      );
    } finally {
      setBusyId(null);
    }
  }

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPendingPage(0);
    setConfirmedPage(0);
    setSearch(searchInput.trim());
  }

  function renderCard(row: Result, editableConfirmed = false) {
    const draft = drafts[row.image_id] ?? initialDraft(row);
    const busy = busyId === row.image_id || recognizingId === row.image_id;
    return (
      <article className="result-card" key={row.image_id}>
        <button
          type="button"
          className="result-preview"
          style={{ aspectRatio: `${row.image_width} / ${row.image_height}` }}
          onClick={(event) => openImagePreview(row, event.currentTarget)}
          aria-label={`Phóng lớn ảnh ${row.original_filename}`}
        >
          {/* Authenticated image URLs cannot be optimized server-side. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/v1/images/${row.image_id}/thumbnail`}
            alt={`Ảnh đồng hồ ${row.original_filename}`}
            loading="lazy"
          />
          {row.ai_reading_bbox && (
            <span
              className="result-region-overlay automatic"
              style={bboxStyle(row.ai_reading_bbox)}
              aria-hidden="true"
            />
          )}
          {draft.readingBbox && (
            <span
              className="result-region-overlay human"
              style={bboxStyle(draft.readingBbox)}
              aria-hidden="true"
            />
          )}
        </button>
        <div className="result-card-body">
          <div className="result-card-heading">
            <div>
              <strong title={row.original_filename}>{row.original_filename}</strong>
              <small>Mã ảnh: {row.image_id.slice(0, 8)}</small>
            </div>
            <span
              className={`badge ${row.final_confidence > 0.9 ? "active" : "warning"}`}
            >
              {confidenceLabel(row.final_confidence)}
            </span>
          </div>
          <div className="region-legend" aria-label="Chú thích vùng nhận diện">
            <span><i className="automatic" aria-hidden="true" />Tự động</span>
            <span><i className="human" aria-hidden="true" />Người dùng</span>
          </div>
          {editableConfirmed && (
            <>
              <span className="result-origin">
                {row.auto_confirmed ? "AI tự động xác nhận" : "Đã kiểm duyệt thủ công"}
              </span>
              <span className={`result-origin ${row.customer_match_status === "MATCHED" ? "matched" : "unmatched"}`}>
                {row.customer_match_status === "MATCHED"
                  ? `Đã khớp: ${row.matched_customer_name ?? row.final_customer_id}${row.matched_meter_serial ? ` · ${row.matched_meter_serial}` : ""}`
                  : "Không tìm thấy mã trong dữ liệu khách hàng"}
              </span>
            </>
          )}
          <div className="result-fields">
            <label>
              Mã khách hàng
              <input
                value={draft.customer}
                onChange={(event) =>
                  updateDraft(row.image_id, "customer", event.target.value)
                }
                disabled={busy}
              />
            </label>
            <label>
              Số điện (kWh)
              <input
                value={draft.reading}
                inputMode="numeric"
                onChange={(event) =>
                  updateDraft(row.image_id, "reading", event.target.value)
                }
                disabled={busy}
              />
            </label>
          </div>
          <div className="result-actions">
            <button
              type="button"
              className="secondary"
              onClick={(event) => openImagePreview(row, event.currentTarget)}
              disabled={busy}
            >
              {draft.readingBbox ? "Sửa vùng chỉ số" : "Khoanh vùng chỉ số"}
            </button>
            {editableConfirmed ? (
              <button
                type="button"
                onClick={() => void submitReview(row, "CONFIRM")}
                disabled={busy || !draft.customer.trim() || !draft.reading.trim()}
              >
                {busy ? "Đang lưu…" : "Lưu thay đổi"}
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => void submitReview(row, "CONFIRM")}
                  disabled={busy || !draft.customer.trim() || !draft.reading.trim()}
                >
                  {busy ? "Đang lưu…" : "Xác nhận"}
                </button>
                <button
                  className="danger"
                  type="button"
                  onClick={() => void submitReview(row, "REJECT")}
                  disabled={busy}
                >
                  Từ chối
                </button>
              </>
            )}
          </div>
        </div>
      </article>
    );
  }

  return (
    <section className="panel full-span operations-results" aria-labelledby="operations-results-title">
      <div className="section-heading operations-results-heading">
        <div>
          <p className="eyebrow">Bước 3</p>
          <h2 id="operations-results-title">Kết quả xử lý</h2>
          <p className="muted">
            Kết quả có độ tin cậy trên 90% được tự động xác nhận. Mọi chỉnh sửa
            sau xác nhận đều được lưu vào nhật ký truy vết.
          </p>
        </div>
        <button className="secondary" type="button" onClick={() => void load()} disabled={loading}>
          Làm mới
        </button>
      </div>
      <form className="operations-search" onSubmit={applySearch} role="search">
        <label htmlFor="operations-result-search">Tìm theo tên ảnh, mã khách hàng hoặc số điện</label>
        <div className="inline-controls">
          <input
            id="operations-result-search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Ví dụ: KH004 hoặc 63751"
          />
          <button type="submit" className="secondary">Tìm kiếm</button>
        </div>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="notice" role="status">{message}</p>}
      <div className="review-board" aria-busy={loading}>
        <section className="review-lane needs-review" aria-labelledby="needs-review-title">
          <div className="review-lane-heading">
            <div>
              <p className="eyebrow">Cần xử lý</p>
              <h3 id="needs-review-title">Chờ kiểm duyệt</h3>
            </div>
            <span className="lane-count" aria-label={`${pending.length} kết quả trên trang`}>
              {pendingTotal}
            </span>
          </div>
          {loading && !pending.length ? (
            <p className="empty-state" role="status">Đang tải hàng chờ…</p>
          ) : pending.length ? (
            <div className="result-list">{pending.map((row) => renderCard(row))}</div>
          ) : (
            <p className="empty-state">Không có kết quả nào cần kiểm duyệt.</p>
          )}
          <Pagination
            pageIndex={pendingPage}
            totalPages={Math.max(1, Math.ceil(pendingTotal / pageSize))}
            onPageChange={setPendingPage}
            ariaLabel="Phân trang hàng chờ kiểm duyệt"
            disabled={loading}
            itemSummary={`${pendingTotal} kết quả`}
          />
        </section>
        <section className="review-lane confirmed-lane" aria-labelledby="confirmed-title">
          <div className="review-lane-heading">
            <div>
              <p className="eyebrow">Hoàn tất</p>
              <h3 id="confirmed-title">Đã xác nhận</h3>
            </div>
            <span className="lane-count success" aria-label={`${confirmed.length} kết quả trên trang`}>
              {confirmedTotal}
            </span>
          </div>
          {loading && !confirmed.length ? (
            <p className="empty-state" role="status">Đang tải kết quả…</p>
          ) : confirmed.length ? (
            <div className="result-list">{confirmed.map((row) => renderCard(row, true))}</div>
          ) : (
            <p className="empty-state">Chưa có kết quả nào được xác nhận.</p>
          )}
          <Pagination
            pageIndex={confirmedPage}
            totalPages={Math.max(1, Math.ceil(confirmedTotal / pageSize))}
            onPageChange={setConfirmedPage}
            ariaLabel="Phân trang kết quả đã xác nhận"
            disabled={loading}
            itemSummary={`${confirmedTotal} kết quả`}
          />
        </section>
      </div>
      {imagePreview && (
        <dialog
          ref={previewDialogRef}
          className="image-preview-dialog"
          aria-labelledby="image-preview-title"
          onClose={finishImagePreview}
          onClick={(event) => {
            if (event.target === event.currentTarget) closeImagePreview();
          }}
        >
          <div className="image-preview-toolbar">
            <div>
              <p className="eyebrow">Ảnh đồng hồ điện</p>
              <h3 id="image-preview-title">{imagePreview.filename}</h3>
            </div>
            <button
              type="button"
              className="secondary image-preview-close"
              onClick={closeImagePreview}
            >
              Đóng
            </button>
          </div>
          <div className="image-preview-canvas annotation-canvas">
            <ReadingRegionAnnotator
              imageUrl={`/api/v1/images/${imagePreview.imageId}/preview`}
              imageAlt={`Ảnh đồng hồ ${imagePreview.filename}`}
              value={drafts[imagePreview.imageId]?.readingBbox ?? null}
              automaticValue={imagePreview.automaticBbox}
              onChange={(value) => updateReadingBbox(imagePreview.imageId, value)}
              onRecognize={() => void recognizeSelectedReading()}
              recognizing={recognizingId === imagePreview.imageId}
              recognitionStatus={recognitionStatus}
              canRecognize={imagePreview.canRecognize}
            />
          </div>
        </dialog>
      )}
    </section>
  );
}
