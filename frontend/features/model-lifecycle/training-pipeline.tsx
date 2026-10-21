"use client";

import { useCallback, useEffect, useState } from "react";

import { usePolling } from "@/hooks/use-polling";
import { useLatestRequest } from "@/hooks/use-latest-request";
import { useLeaveGuard } from "@/hooks/use-leave-guard";
import { usePanelActive } from "@/components/section-tabs";
import { ConfirmationDialog } from "@/components/confirmation-dialog";
import { useConfirmationDialog } from "@/hooks/use-confirmation-dialog";
import { trainingStatusLabel } from "@/lib/training-status";
import {
  getTrainingOverview,
  startTraining,
  cancelTraining,
  type TrainingOptions,
  type TrainingOverview,
} from "@/services/administration";

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
  CANCELLED: "Đã hủy",
  FINE_TUNING_SEQUENCE_READER: "Fine-tune PARSeq-tiny",
  EVALUATING_HOLDOUT: "Đánh giá kiểm tra độc lập",
  TRAINING_DEEP_LOCATORS: "Học và đối chứng định vị MobileNetV3",
};

export function TrainingPipeline({ csrfToken }: { csrfToken: string }) {
  const panelActive = usePanelActive();
  const confirmation = useConfirmationDialog();
  const [options, setOptions] = useState<TrainingOptions>({ experimental: false, fine_tune_reader: true, epochs: 10, batch_size: 8, learning_rate: 0.0001, benchmark_deep_locator: false, deep_locator_epochs: 40 });
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
    if (busy || active || loading || (!overview?.dataset.ready && !options.experimental)) return;
    if (!(await confirmation.ask({ title: "Tạo phiên huấn luyện?", description: options.experimental ? "Phiên chẩn đoán có thể dùng nhóm chưa xác minh, không được kích hoạt. Holdout vẫn bị loại khỏi dữ liệu học." : "Hệ thống đóng băng nhãn và phân tập, học vùng công tơ/vùng số và fine-tune bộ đọc nếu đã chọn. Không tự kích hoạt mô hình.", confirmLabel: "Tạo phiên" }))) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await startTraining(csrfToken, options);
      setNotice("Đã tạo phiên huấn luyện. Trainer sẽ xử lý ở tiến trình riêng.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể bắt đầu huấn luyện.");
    } finally {
      setBusy(false);
    }
  }

  const dataset = overview?.dataset;
  async function cancel(id: string) {
    if (busy || !(await confirmation.ask({ title: "Hủy phiên huấn luyện?", description: "Trainer sẽ dừng ở điểm kiểm tra tiếp theo. Các mô hình đang hoạt động không bị thay đổi.", confirmLabel: "Hủy phiên", danger: true }))) return;
    setBusy(true); setError(null);
    try { await cancelTraining(id, csrfToken); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể hủy phiên."); }
    finally { setBusy(false); }
  }
  return (
    <section className="panel full-span" aria-labelledby="training-title">
      <ConfirmationDialog confirmation={confirmation} />
      <div className="section-heading training-heading">
        <div>
          <p className="eyebrow">Pipeline dữ liệu</p>
          <h2 id="training-title">Huấn luyện từ ảnh đã kiểm duyệt</h2>
          <p className="muted">
            Tải ảnh tại trang Vận hành, sửa và xác nhận nhãn. Khi đủ mẫu, hệ thống
            học vùng toàn bộ công tơ và vùng số trong mặt công tơ đã chỉnh phối cảnh, fine-tune PARSeq-tiny;
            PP-OCRv6/PARSeq có sẵn được dùng làm đối chứng,
            sau đó đăng ký mô hình ở trạng thái thử nghiệm để đánh giá trước khi kích hoạt.
          </p>
        </div>
        <div className="inline-controls"><button type="button" className="secondary" onClick={() => void load()} disabled={busy || loading}>Làm mới</button>
        <button type="button" onClick={() => void start()} disabled={busy || loading || active || (!dataset?.ready && !(options.experimental && (dataset?.eligible_samples ?? 0) >= 3))}>
          {active ? "Đang xử lý…" : busy ? "Đang tạo…" : "Huấn luyện ngay"}
        </button>
        </div>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {overview?.runs[0]?.status === "FAILED" && <p className="notice" role="status">Huấn luyện tự động đang tạm dừng sau lỗi. Kiểm tra nguyên nhân, sửa dữ liệu hoặc cấu hình rồi bấm Huấn luyện ngay. Chỉ sau một phiên thành công hệ thống mới tự huấn luyện tiếp.</p>}
      {dataset && <section className="training-readiness" aria-label="Mức sẵn sàng huấn luyện">
        <div><strong>{active ? "Một phiên đang được xử lý" : dataset.ready ? "Dữ liệu đã đủ điều kiện huấn luyện" : "Cần hoàn thiện dữ liệu huấn luyện"}</strong>
          <p>{dataset.training_samples + dataset.validation_samples} mẫu học đã xác minh / ngưỡng {dataset.minimum_samples}. Mẫu holdout không tính vào ngưỡng học.</p></div>
        <progress value={Math.min(dataset.training_samples + dataset.validation_samples, Math.max(1, dataset.minimum_samples))} max={Math.max(1, dataset.minimum_samples)} aria-label="Mẫu học đã xác minh so với ngưỡng huấn luyện" />
      </section>}
      <div className="metrics training-metrics">
        <div><strong>{dataset?.uploaded_images ?? "—"}</strong><span>Ảnh đã tải</span></div>
        <div><strong>{dataset?.confirmed_images ?? "—"}</strong><span>Đã gắn nhãn</span></div>
        <div><strong>{dataset?.verified_samples ?? "—"}</strong><span>Mẫu đã xác minh</span></div>
        <div><strong>{dataset?.minimum_samples ?? "—"}</strong><span>Ngưỡng huấn luyện</span></div>
      </div>
      <p className="read-only-note">
        {!dataset ? "Đang tải chính sách huấn luyện…" : dataset.auto_start_enabled
          ? `Tự động huấn luyện đang bật. Còn ${Math.max(0, dataset.minimum_samples - dataset.training_samples - dataset.validation_samples)} mẫu học đã xác minh để đạt ngưỡng.`
          : "Tự động huấn luyện đang tắt. Có thể bật trong Cấu hình hệ thống."}
        {" "}Chỉ ảnh duy nhất có số điện đúng, vùng toàn bộ công tơ và vùng dãy số
        đã được người dùng lưu nhãn mới được đưa vào tập huấn luyện; không bắt buộc có mã khách hàng.
        {" "}Để kiểm định trước khi kích hoạt, cần bổ sung định danh công tơ hoặc mã khách hàng
        nhằm tách ảnh của cùng một công tơ vào cùng một nhóm, có ít nhất 30 ảnh chọn trọng số và 30 ảnh kiểm tra độc lập.
        Pipeline đã hỗ trợ fine-tune bộ đọc chuỗi số. Điểm tin cậy chưa được hiệu chuẩn; tự xác nhận vẫn khóa.
      </p>
      <p className="muted">Huấn luyện: {dataset?.training_samples ?? "—"} · Chọn trọng số: {dataset?.validation_samples ?? "—"} · Kiểm tra độc lập: {dataset?.holdout_samples ?? "—"} · Chưa xác minh nhóm: {dataset?.unverified_identity_samples ?? "—"}</p>
      {dataset?.data_issues.map((message) => <p className="error" key={message}>{message}</p>)}
      <fieldset disabled={busy || active} className="settings-grid">
        <label className="checkbox-label"><input type="checkbox" checked={options.fine_tune_reader} onChange={(event) => setOptions({ ...options, fine_tune_reader: event.target.checked })} /> Fine-tune bộ đọc PARSeq-tiny</label>
        <label>Số epoch<input type="number" min={1} max={100} value={options.epochs} onChange={(event) => setOptions({ ...options, epochs: Number(event.target.value) })} /></label>
        <label>Kích thước lô học<input type="number" min={1} max={64} value={options.batch_size} onChange={(event) => setOptions({ ...options, batch_size: Number(event.target.value) })} /></label>
        <label>Tốc độ học<input type="number" min={0.000001} max={0.01} step={0.00001} value={options.learning_rate} onChange={(event) => setOptions({ ...options, learning_rate: Number(event.target.value) })} /></label>
        <label className="checkbox-label"><input type="checkbox" checked={options.experimental} onChange={(event) => setOptions({ ...options, experimental: event.target.checked })} /> Chạy chẩn đoán với ít dữ liệu (không được kích hoạt)</label>
        <label className="checkbox-label"><input type="checkbox" checked={options.benchmark_deep_locator} onChange={(event) => setOptions({ ...options, benchmark_deep_locator: event.target.checked })} /> Học MobileNetV3 và so sánh định vị với Ridge (không tự thay mô hình)</label>
        {options.benchmark_deep_locator && <label>Epoch bộ định vị<input type="number" min={1} max={100} value={options.deep_locator_epochs} onChange={(event) => setOptions({ ...options, deep_locator_epochs: Number(event.target.value) })} /><small>Backbone pretrained cố định; học đầu dự đoán bốn góc trên CPU.</small></label>}
      </fieldset>
      <h3>Lịch sử huấn luyện & đánh giá</h3>
      <div className="table-wrap training-table" aria-busy={loading}>
        <table>
          <thead><tr><th className="row-number">STT</th><th>Thời điểm</th><th>Trạng thái</th><th>Tiến trình</th><th>Dataset</th><th>Kết quả</th></tr></thead>
          <tbody>
            {(overview?.runs ?? []).map((run, index) => (
              <tr key={run.id}>
                <td className="row-number">{index + 1}</td>
                <td>{new Date(run.created_at).toLocaleString("vi-VN")}<small>{run.trigger === "AUTO" ? "Tự động" : "Thủ công"}</small></td>
                <td><span className={`badge ${run.status === "COMPLETED" ? "success" : run.status === "FAILED" ? "warning" : "active"}`}>{trainingStatusLabel(run.status)}</span></td>
                <td>
                  {["PENDING", "RUNNING"].includes(run.status) && <button type="button" className="secondary" disabled={busy} onClick={() => void cancel(run.id)}>Hủy phiên</button>}
                  <div className="training-progress"><span style={{ width: `${run.progress}%` }} /></div>
                  <small>{stageLabels[run.stage] ?? run.stage} · {run.progress}%</small>
                  {typeof run.metrics.training_epoch === "number" && <small>Epoch {run.metrics.training_epoch} / {String(run.metrics.training_epochs ?? "—")} · Loss {typeof run.metrics.training_loss === "number" ? run.metrics.training_loss.toFixed(4) : "—"}</small>}
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
                  {typeof run.metrics.holdout_images === "number" && <small>{run.metrics.holdout_images} ảnh kiểm tra độc lập · {run.metrics.independent_holdout === true ? "Đã tách theo nhóm" : "Chỉ chẩn đoán"}</small>}
                  {run.metrics.locator_benchmark != null && <small>Có đối chứng Ridge / MobileNetV3. Xem chi tiết tại Kho mô hình; không tự kích hoạt.</small>}
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
