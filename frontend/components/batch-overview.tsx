"use client";

import { useEffect, useState } from "react";

import { getBatches } from "@/services/batches";
import type { Batch } from "@/types/batch";

const activeStatuses = new Set(["UPLOADING", "QUEUED", "PROCESSING"]);
const pageSize = 8;
const statusLabels: Record<string, string> = {
  CREATED: "Đã tạo",
  UPLOADING: "Đang tải lên",
  READY: "Sẵn sàng",
  QUEUED: "Đang chờ xử lý",
  PROCESSING: "Đang xử lý",
  COMPLETED: "Hoàn tất",
  PARTIAL_FAILED: "Hoàn tất một phần",
  FAILED: "Thất bại",
  CANCELLED: "Đã hủy",
};

export function BatchOverview() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(showLoading = false) {
    if (showLoading) setLoading(true);
    try {
      setBatches(await getBatches(page * pageSize, pageSize));
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
  }

  useEffect(() => {
    void load(true);
    const timer = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [page]);

  const active = batches.filter((batch) =>
    activeStatuses.has(batch.status),
  ).length;
  return (
    <section className="panel" aria-labelledby="batch-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Vận hành</p>
          <h2 id="batch-title">Các lô dữ liệu</h2>
        </div>
        <span className={active ? "badge active" : "badge"}>
          {active ? `${active} lô đang xử lý` : "Đã xử lý xong"}
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
        <p className="muted">Trang này chưa có lô dữ liệu nào.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Lô dữ liệu</th>
                <th>Trạng thái</th>
                <th>Tiến độ</th>
                <th>Kiểm duyệt</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => (
                <tr key={batch.id}>
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
                    {batch.review_count} cần duyệt · {batch.failed_count} lỗi
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
          onClick={() => setPage((current) => Math.max(0, current - 1))}
          disabled={page === 0 || loading}
        >
          Trước
        </button>
        <span>Trang {page + 1}</span>
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => current + 1)}
          disabled={batches.length < pageSize || loading}
        >
          Sau
        </button>
      </nav>
    </section>
  );
}
