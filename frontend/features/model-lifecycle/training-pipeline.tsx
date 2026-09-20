"use client";

import { useCallback, useEffect, useState } from "react";

import { usePolling } from "@/hooks/use-polling";
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
  REGISTERING_MODEL: "Đăng ký model",
  COMPLETED: "Hoàn tất",
  FAILED: "Thất bại",
};

export function TrainingPipeline({ csrfToken }: { csrfToken: string }) {
  const [overview, setOverview] = useState<TrainingOverview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setOverview(await getTrainingOverview());
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải pipeline huấn luyện.");
    }
  }, []);

  useEffect(() => void load(), [load]);
  const active = overview?.runs.some((run) => run.status === "PENDING" || run.status === "RUNNING") ?? false;
  usePolling(load, 5000, active);

  async function start() {
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
            Ảnh tải lên được OCR và kiểm duyệt. Khi đủ mẫu, hệ thống tự tạo dataset,
            chia train/validation, huấn luyện và đăng ký model ở trạng thái thử nghiệm.
          </p>
        </div>
        <button type="button" onClick={() => void start()} disabled={busy || active || !dataset?.ready}>
          {active ? "Đang xử lý…" : busy ? "Đang tạo…" : "Huấn luyện ngay"}
        </button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      <div className="metrics training-metrics">
        <div><strong>{dataset?.uploaded_images ?? "—"}</strong><span>Ảnh đã tải</span></div>
        <div><strong>{dataset?.confirmed_images ?? "—"}</strong><span>Đã xác nhận</span></div>
        <div><strong>{dataset?.eligible_samples ?? "—"}</strong><span>Mẫu đủ điều kiện</span></div>
        <div><strong>{dataset?.minimum_samples ?? "—"}</strong><span>Ngưỡng huấn luyện</span></div>
      </div>
      <p className="read-only-note">
        {dataset?.auto_start_enabled
          ? `Tự động huấn luyện đang bật. Còn ${Math.max(0, (dataset.minimum_samples ?? 0) - (dataset.eligible_samples ?? 0))} mẫu để đạt ngưỡng.`
          : "Tự động huấn luyện đang tắt. Có thể bật trong Cấu hình hệ thống."}
        {" "}Chỉ mẫu được con người xác nhận mới được sử dụng.
      </p>
      <div className="table-wrap training-table">
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
                <td>{run.sample_count} mẫu<small>{run.training_count} train · {run.validation_count} validation</small></td>
                <td>{run.error_message ?? (run.model_id ? "Model đã đăng ký" : "—")}</td>
              </tr>
            ))}
            {!overview?.runs.length && <tr><td colSpan={6}>Chưa có phiên huấn luyện.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
