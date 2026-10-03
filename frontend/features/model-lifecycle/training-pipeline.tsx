"use client";

import { useCallback, useEffect, useState } from "react";

import { usePolling } from "@/hooks/use-polling";
import { useLatestRequest } from "@/hooks/use-latest-request";
import { useLeaveGuard } from "@/hooks/use-leave-guard";
import { usePanelActive } from "@/components/section-tabs";
import {
  getTrainingOverview,
  startTraining,
  type TrainingOverview,
} from "@/services/administration";

const statusLabels: Record<string, string> = {
  PENDING: "Đang chờ",
  RUNNING: "Đang huấn luyện",
  COMPLETED: "Hoàn tất",
  FAILED: "Thất bại",
};
const stageLabels: Record<string, string> = {
  QUEUED: "Đã xếp hàng",
  PREPARING_DATASET: "Chuẩn bị dataset",
  EXTRACTING_FEATURES: "Trích xuất đặc trưng",
  VALIDATING: "Đánh giá tập validation",
  BUILDING_SEQUENCE_DATASET: "Tạo bộ dữ liệu chuỗi số",
  BENCHMARKING_SEQUENCE_READER: "Đánh giá PP-OCRv6 và PARSeq",
  REGISTERING_MODEL: "Đăng ký model",
  COMPLETED: "Hoàn tất",
  FAILED: "Thất bại",
};

export function TrainingPipeline({ csrfToken }: { csrfToken: string }) {
  const panelActive = usePanelActive();
  const request = useLatestRequest();
  const [overview, setOverview] = useState<TrainingOverview | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  useLeaveGuard(false, busy, "tạo phiên huấn luyện");

  const load = useCallback(async () => {
    const revision = request.begin();
    try {
      const result = await getTrainingOverview();
      if (!request.isCurrent(revision)) return;
      setOverview(result);
      setError(null);
    } catch (reason) {
      if (!request.isCurrent(revision)) return;
      setError(reason instanceof Error ? reason.message : "Không thể tải pipeline huấn luyện.");
    } finally {
      if (request.isCurrent(revision)) setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (!panelActive) return;
    void load();
    const refresh = () => { void load(); };
    window.addEventListener("training-data-changed", refresh);
    return () => { window.removeEventListener("training-data-changed", refresh); request.invalidate(); };
  }, [load, panelActive, request]);
  const active = overview?.runs.some((run) => run.status === "PENDING" || run.status === "RUNNING") ?? false;
  usePolling(load, 5000, active && panelActive);

  async function start() {
    if (busy || active || loading || !overview?.dataset.ready) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await startTraining(csrfToken);
      setNotice("Đã tạo phiên huấn luyện. Trainer sẽ xử lý ở tiến trình riêng.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể bắt đầu huấn luyện.");
    } finally {
      setBusy(false);
    }
  }

  const dataset = overview?.dataset;
  return (
    <section className="panel full-span" aria-labelledby="training-title">
      <div className="section-heading training-heading">
        <div>
          <p className="eyebrow">Pipeline dữ liệu</p>
          <h2 id="training-title">Huấn luyện từ ảnh đã kiểm duyệt</h2>
          <p className="muted">
            Tải ảnh tại trang Vận hành, sửa và xác nhận nhãn. Khi đủ mẫu, hệ thống
            học vùng toàn bộ công tơ và bốn góc vùng chỉ số. Chuỗi số được đọc bằng PP-OCRv6/PARSeq;
            nhãn đã xác nhận được dùng để benchmark hai bộ đọc trước khi thay đổi mô hình,
            sau đó đăng ký mô hình ở trạng thái thử nghiệm để đánh giá trước khi kích hoạt.
          </p>
        </div>
        <div className="inline-controls"><button type="button" className="secondary" onClick={() => void load()} disabled={busy || loading}>Làm mới</button>
        <button type="button" onClick={() => void start()} disabled={busy || loading || active || !dataset?.ready}>
          {active ? "Đang xử lý…" : busy ? "Đang tạo…" : "Huấn luyện ngay"}
        </button>
        </div>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      <div className="metrics training-metrics">
        <div><strong>{dataset?.uploaded_images ?? "—"}</strong><span>Ảnh đã tải</span></div>
        <div><strong>{dataset?.confirmed_images ?? "—"}</strong><span>Đã gắn nhãn</span></div>
        <div><strong>{dataset?.eligible_samples ?? "—"}</strong><span>Mẫu đủ điều kiện</span></div>
        <div><strong>{dataset?.minimum_samples ?? "—"}</strong><span>Ngưỡng huấn luyện</span></div>
      </div>
      <p className="read-only-note">
        {!dataset ? "Đang tải chính sách huấn luyện…" : dataset.auto_start_enabled
          ? `Tự động huấn luyện đang bật. Còn ${Math.max(0, (dataset.minimum_samples ?? 0) - (dataset.eligible_samples ?? 0))} mẫu để đạt ngưỡng.`
          : "Tự động huấn luyện đang tắt. Có thể bật trong Cấu hình hệ thống."}
        {" "}Chỉ ảnh duy nhất có số điện đúng, vùng toàn bộ công tơ và vùng dãy số
        đã được người dùng lưu nhãn mới được đưa vào tập huấn luyện; không bắt buộc có mã khách hàng.
      </p>
      <div className="table-wrap training-table" aria-busy={loading}>
        <table>
          <thead><tr><th className="row-number">STT</th><th>Thời điểm</th><th>Trạng thái</th><th>Tiến trình</th><th>Dataset</th><th>Kết quả</th></tr></thead>
          <tbody>
            {(overview?.runs ?? []).map((run, index) => (
              <tr key={run.id}>
                <td className="row-number">{index + 1}</td>
                <td>{new Date(run.created_at).toLocaleString("vi-VN")}<small>{run.trigger === "AUTO" ? "Tự động" : "Thủ công"}</small></td>
                <td><span className={`badge ${run.status === "COMPLETED" ? "success" : run.status === "FAILED" ? "warning" : "active"}`}>{statusLabels[run.status] ?? run.status}</span></td>
                <td>
                  <div className="training-progress"><span style={{ width: `${run.progress}%` }} /></div>
                  <small>{stageLabels[run.stage] ?? run.stage} · {run.progress}%</small>
                </td>
                <td>{run.sample_count} mẫu<small>{run.training_count} huấn luyện · {run.validation_count} kiểm định</small></td>
                <td>
                  {run.error_message ?? (run.model_id ? "Mô hình đã đăng ký" : "—")}
                  {typeof run.metrics.validation_reading_exact_accuracy === "number" && (
                    <small>{`${Math.round(run.metrics.validation_reading_exact_accuracy * 1000) / 10}% đọc đúng toàn chuỗi`}</small>
                  )}
                  {typeof run.metrics.sequence_reader_coverage === "number" && (
                    <small>{`${Math.round(run.metrics.sequence_reader_coverage * 1000) / 10}% có kết quả đồng thuận`}</small>
                  )}
                  {run.metrics.sequence_reader_unavailable === true && (
                    <small>Không thể kết nối bộ đọc khi benchmark</small>
                  )}
                </td>
              </tr>
            ))}
            {loading && <tr><td colSpan={6} role="status">Đang tải lịch sử huấn luyện…</td></tr>}
            {!loading && !error && !overview?.runs.length && <tr><td colSpan={6}>Chưa có phiên huấn luyện.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
