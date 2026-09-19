"use client";

import { useCallback, useEffect, useState } from "react";

import { getBatchImages, getBatchesPage } from "@/services/batches";
import type { Batch, BatchImage } from "@/types/batch";

const activeStatuses = new Set(["UPLOADING", "QUEUED", "PROCESSING"]);
const batchPageSize = 10;
const imagePageSize = 12;
const statusLabels: Record<string, string> = {
  CREATED: "Đã tạo",
  UPLOADING: "Đang tải lên",
  UPLOADED: "Đã tải lên",
  READY: "Sẵn sàng",
  QUEUED: "Đang chờ xử lý",
  PROCESSING: "Đang xử lý",
  AI_COMPLETED: "AI đã xử lý",
  REVIEW_REQUIRED: "Cần kiểm duyệt",
  CONFIRMED: "Đã xác nhận",
  REJECTED: "Đã từ chối",
  COMPLETED: "Hoàn tất",
  PARTIAL_FAILED: "Hoàn tất một phần",
  FAILED: "Thất bại",
  CANCELLED: "Đã hủy",
};

const pageCount = (total: number, size: number) =>
  Math.max(1, Math.ceil(total / size));
const fileSize = (value: number) =>
  value >= 1024 * 1024
    ? `${(value / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(value / 1024))} KB`;

export function BatchOverview() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [batchTotal, setBatchTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Batch | null>(null);
  const [images, setImages] = useState<BatchImage[]>([]);
  const [imageTotal, setImageTotal] = useState(0);
  const [imagePage, setImagePage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadBatches = useCallback(
    async (showLoading = false) => {
      if (showLoading) setLoading(true);
      try {
        const result = await getBatchesPage(
          page * batchPageSize,
          batchPageSize,
        );
        setBatches(result.items);
        setBatchTotal(result.total);
        setSelected((current) =>
          current
            ? result.items.find((batch) => batch.id === current.id) ?? current
            : null,
        );
        setError(null);
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Không thể tải danh sách lô.",
        );
      } finally {
        setLoading(false);
      }
    },
    [page],
  );

  const loadImages = useCallback(
    async (showLoading = false) => {
      if (!selected) return;
      if (showLoading) setDetailLoading(true);
      try {
        const result = await getBatchImages(
          selected.id,
          imagePage * imagePageSize,
          imagePageSize,
        );
        setImages(result.items);
        setImageTotal(result.total);
        setError(null);
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Không thể tải chi tiết lô dữ liệu.",
        );
      } finally {
        setDetailLoading(false);
      }
    },
    [imagePage, selected],
  );

  useEffect(() => {
    void loadBatches(true);
    const timer = window.setInterval(() => void loadBatches(), 5000);
    return () => window.clearInterval(timer);
  }, [loadBatches]);

  useEffect(() => {
    if (!selected) {
      setImages([]);
      setImageTotal(0);
      return;
    }
    void loadImages(true);
    const timer = window.setInterval(() => void loadImages(), 5000);
    return () => window.clearInterval(timer);
  }, [loadImages, selected]);

  function selectBatch(batch: Batch) {
    setSelected(batch);
    setImagePage(0);
  }

  const active = batches.filter((batch) =>
    activeStatuses.has(batch.status),
  ).length;
  const batchPages = pageCount(batchTotal, batchPageSize);
  const imagePages = pageCount(imageTotal, imagePageSize);

  return (
    <section className="panel full-span" aria-labelledby="batch-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Lịch sử xử lý</p>
          <h2 id="batch-title">Các lô dữ liệu</h2>
          <p className="muted batch-description">
            Chọn một lô để xem toàn bộ hình ảnh, trạng thái xử lý và kết quả nhận diện.
          </p>
        </div>
        <span className={active ? "badge active" : "badge"}>
          {active
            ? `${active} lô đang xử lý trên trang`
            : `${batchTotal} lô dữ liệu`}
        </span>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p className="muted" role="status">
          Đang tải danh sách lô…
        </p>
      ) : batches.length === 0 ? (
        <p className="empty-state">Chưa có lô dữ liệu nào được tải lên.</p>
      ) : (
        <div className="table-wrap batch-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Lô dữ liệu</th>
                <th>Trạng thái</th>
                <th>Tiến độ</th>
                <th>Kết quả</th>
                <th>Ngày tạo</th>
                <th>Chi tiết</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => (
                <tr
                  key={batch.id}
                  className={selected?.id === batch.id ? "selected-row" : undefined}
                >
                  <td>
                    <strong>{batch.original_folder_name}</strong>
                    <small>{batch.batch_code}</small>
                  </td>
                  <td>
                    <span className="badge">
                      {statusLabels[batch.status] ?? batch.status}
                    </span>
                  </td>
                  <td>
                    Đã xử lý {batch.processed_images}/{batch.total_images}
                  </td>
                  <td>
                    {batch.ok_count} xác nhận · {batch.review_count} cần duyệt
                    <small>
                      {batch.ng_count} từ chối · {batch.failed_count} lỗi
                    </small>
                  </td>
                  <td>{new Date(batch.created_at).toLocaleString("vi-VN")}</td>
                  <td>
                    <button
                      className="secondary table-detail-button"
                      type="button"
                      aria-expanded={selected?.id === batch.id}
                      onClick={() => selectBatch(batch)}
                    >
                      Xem chi tiết
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav className="pagination" aria-label="Phân trang danh sách lô">
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((value) => Math.max(0, value - 1))}
          disabled={page === 0 || loading}
        >
          Trước
        </button>
        <span>
          Trang {page + 1} / {batchPages} · {batchTotal} lô
        </span>
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((value) => value + 1)}
          disabled={page + 1 >= batchPages || loading}
        >
          Sau
        </button>
      </nav>

      {selected && (
        <section className="batch-detail" aria-labelledby="batch-detail-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Chi tiết lô</p>
              <h3 id="batch-detail-title">{selected.original_folder_name}</h3>
              <p className="muted">
                {selected.batch_code} · {selected.total_images} hình ảnh
              </p>
            </div>
            <button
              className="secondary"
              type="button"
              onClick={() => void loadImages(true)}
              disabled={detailLoading}
            >
              Làm mới
            </button>
          </div>
          {detailLoading && !images.length ? (
            <p className="muted" role="status">
              Đang tải hình ảnh trong lô…
            </p>
          ) : images.length === 0 ? (
            <p className="empty-state">Lô này chưa có hình ảnh.</p>
          ) : (
            <div className="table-wrap batch-images-table">
              <table>
                <thead>
                  <tr>
                    <th>Hình ảnh</th>
                    <th>Trạng thái</th>
                    <th>Mã khách hàng</th>
                    <th>Số điện</th>
                    <th>Độ tin cậy</th>
                    <th>Kích thước</th>
                  </tr>
                </thead>
                <tbody>
                  {images.map((image) => (
                    <tr key={image.image_id}>
                      <td>
                        <div className="batch-image-cell">
                          <a
                            href={`/api/v1/images/${image.image_id}/preview`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            <img
                              src={`/api/v1/images/${image.image_id}/preview`}
                              alt={`Ảnh ${image.original_filename}`}
                              loading="lazy"
                            />
                          </a>
                          <span>
                            <strong>{image.original_filename}</strong>
                            <small>{fileSize(image.file_size)}</small>
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="badge">
                          {statusLabels[image.image_status] ?? image.image_status}
                        </span>
                      </td>
                      <td>
                        {image.final_customer_id ?? image.customer_id_ai ?? "—"}
                      </td>
                      <td>
                        {image.final_meter_reading ?? image.meter_reading_ai ?? "—"}
                      </td>
                      <td>
                        {image.final_confidence === null
                          ? "—"
                          : `${Math.round(image.final_confidence * 100)}%`}
                      </td>
                      <td>
                        {image.width} × {image.height}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <nav className="pagination" aria-label="Phân trang hình ảnh trong lô">
            <button
              className="secondary"
              type="button"
              onClick={() => setImagePage((value) => Math.max(0, value - 1))}
              disabled={imagePage === 0 || detailLoading}
            >
              Trước
            </button>
            <span>
              Trang {imagePage + 1} / {imagePages} · {imageTotal} hình ảnh
            </span>
            <button
              className="secondary"
              type="button"
              onClick={() => setImagePage((value) => value + 1)}
              disabled={imagePage + 1 >= imagePages || detailLoading}
            >
              Sau
            </button>
          </nav>
        </section>
      )}
    </section>
  );
}
