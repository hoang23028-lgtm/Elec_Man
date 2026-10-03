"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useLatestRequest } from "@/hooks/use-latest-request";
import { useLeaveGuard } from "@/hooks/use-leave-guard";
import { usePanelActive } from "@/components/section-tabs";

import {
  activateModel,
  getEvaluation,
  getModels,
  registerModel,
  type Evaluation,
  type ModelInput,
  type ModelRecord,
} from "@/services/administration";

const emptyInput: ModelInput = {
  model_name: "",
  model_type: "reading_region_ridge",
  version: "",
  file_path: "",
  sha256: "",
  metrics: {},
};
const supportedModelTypes = new Set(["reading_region_ridge", "meter_locator_ridge"]);
const modelTypeLabels: Record<string, string> = {
  reading_region_ridge: "Định vị vùng chỉ số",
  meter_locator_ridge: "Định vị toàn bộ công tơ",
};
const percent = (value: number | null) =>
  value === null ? "Chưa có dữ liệu" : `${Math.round(value * 1000) / 10}%`;
const statusLabels: Record<string, string> = {
  TESTING: "Đang thử nghiệm",
  ACTIVE: "Đang hoạt động",
  ARCHIVED: "Đã lưu trữ",
};

export function ModelOperations({ csrfToken }: { csrfToken: string }) {
  const request = useLatestRequest();
  const panelActive = usePanelActive();
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [input, setInput] = useState<ModelInput>(emptyInput);
  const [metricsJson, setMetricsJson] = useState("{}");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  useLeaveGuard(JSON.stringify(input) !== JSON.stringify(emptyInput) || metricsJson !== "{}", saving, "đăng ký / kích hoạt mô hình");

  const load = useCallback(async () => {
    const revision = request.begin();
    try {
      const [modelRows, summary] = await Promise.all([
        getModels(),
        getEvaluation(),
      ]);
      if (!request.isCurrent(revision)) return;
      setModels(modelRows);
      setEvaluation(summary);
      setError(null);
    } catch (reason) {
      if (!request.isCurrent(revision)) return;
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể tải dữ liệu vòng đời mô hình.",
      );
    } finally {
      if (request.isCurrent(revision)) setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (panelActive) void load();
    return () => request.invalidate();
  }, [load, panelActive, request]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const metrics = JSON.parse(metricsJson) as Record<string, unknown>;
      await registerModel({ ...input, metrics }, csrfToken);
      setInput(emptyInput);
      setMetricsJson("{}");
      setNotice(
        "Gói mô hình đã được xác minh và đăng ký ở trạng thái thử nghiệm.",
      );
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể đăng ký mô hình. Hãy kiểm tra JSON chỉ số.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function activate(record: ModelRecord) {
    if (saving) return;
    if (
      !window.confirm(
        `Kích hoạt ${record.model_name} ${record.version}? Worker sẽ kiểm tra checksum và nạp model cho tác vụ tiếp theo.`,
      )
    )
      return;
    setSaving(true);
    setError(null);
    try {
      await activateModel(record.id, csrfToken);
      setNotice(
        "Đã kích hoạt model. Worker sẽ tự động nạp model đã xác minh cho tác vụ tiếp theo.",
      );
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể kích hoạt mô hình.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel full-span" aria-labelledby="models-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Vòng đời mô hình</p>
          <h2 id="models-title">Kho mô hình và đánh giá</h2>
        </div>
        <span className="badge active">Cần phê duyệt thủ công</span>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      <div className="metrics evaluation-metrics">
        <div>
          <strong>{evaluation?.confirmed_samples ?? "—"}</strong>
          <span>Mẫu đã xác nhận</span>
        </div>
        <div>
          <strong>
            {percent(evaluation?.customer_exact_accuracy ?? null)}
          </strong>
          <span>Đúng mã khách hàng</span>
        </div>
        <div>
          <strong>{percent(evaluation?.meter_exact_accuracy ?? null)}</strong>
          <span>Đúng chỉ số điện</span>
        </div>
        <div>
          <strong>{percent(evaluation?.meter_digit_accuracy ?? null)}</strong>
          <span>Độ chính xác chữ số</span>
        </div>
      </div>
      <p className="muted">
        Các chỉ số chỉ sử dụng mẫu thực tế đã được con người xác nhận, không đại
        diện cho độ chính xác trên tập kiểm thử độc lập.
      </p>
      {loading ? <p className="muted" role="status">Đang tải kho mô hình…</p> : error && models.length === 0 ? null : models.length === 0 ? (
        <p className="muted">
          Chưa có gói mô hình có thể triển khai nào được đăng ký. OCR cơ sở hiện
          được đóng gói cùng tiến trình xử lý và mọi kết quả vẫn cần kiểm duyệt.
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="row-number">STT</th>
                <th>Mô hình</th>
                <th>Loại</th>
                <th>Phiên bản</th>
                <th>Trạng thái</th>
                <th>Đánh giá</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {models.map((record, index) => (
                <tr key={record.id}>
                  <td className="row-number">{index + 1}</td>
                  <td>
                    {record.model_name}
                    <small>{record.file_path}</small>
                  </td>
                  <td>
                    {modelTypeLabels[record.model_type] ?? record.model_type}
                    {!supportedModelTypes.has(record.model_type) && <small>Di sản · chỉ lưu để truy vết</small>}
                  </td>
                  <td>{record.version}</td>
                  <td>
                    <span
                      className={`badge ${record.status === "ACTIVE" ? "active" : ""}`}
                    >
                      {statusLabels[record.status] ?? record.status}
                    </span>
                  </td>
                  <td>
                    {typeof record.metrics.validation_digit_accuracy ===
                    "number"
                      ? `${Math.round(record.metrics.validation_digit_accuracy * 1000) / 10}% chính xác`
                      : "Chưa có"}
                    <small>
                      {typeof record.metrics.digit_coverage === "number"
                        ? `${Math.round(record.metrics.digit_coverage * 10)}/10 chữ số`
                        : "Chưa có độ phủ"}
                    </small>
                    {typeof record.metrics.validation_reading_exact_accuracy === "number" && (
                      <small>
                        {`${Math.round(record.metrics.validation_reading_exact_accuracy * 1000) / 10}% đúng chỉ số trên vùng và số chữ số đã gắn nhãn (không phải toàn quy trình)`}
                      </small>
                    )}
                    {typeof record.metrics.validation_region_accuracy === "number" && (
                      <small>
                        {`Điểm vùng chỉ số: ${Math.round(record.metrics.validation_region_accuracy * 1000) / 10}/100 (quy đổi từ sai số tọa độ)`}
                      </small>
                    )}
                    {typeof record.metrics.validation_meter_region_accuracy === "number" && (
                      <small>
                        {`Điểm vùng công tơ: ${Math.round(record.metrics.validation_meter_region_accuracy * 1000) / 10}/100 (quy đổi từ sai số tọa độ)`}
                      </small>
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      onClick={() => void activate(record)}
                      disabled={saving || record.status === "ACTIVE" || !supportedModelTypes.has(record.model_type)}
                      title={!supportedModelTypes.has(record.model_type) ? "Pipeline hiện tại không hỗ trợ kích hoạt loại mô hình này." : undefined}
                    >
                      {supportedModelTypes.has(record.model_type) ? "Kích hoạt" : "Không hỗ trợ"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <details className="registration">
        <summary>Đăng ký gói mô hình đã xác minh</summary>
        <form className="settings-form" onSubmit={submit}>
          <fieldset className="editor-fields" disabled={saving}>
          <div className="settings-grid">
            <div className="setting-field">
              <label htmlFor="model-name">Tên mô hình</label>
              <input
                id="model-name"
                value={input.model_name}
                onChange={(event) =>
                  setInput((current) => ({
                    ...current,
                    model_name: event.target.value,
                  }))
                }
                required
              />
            </div>
            <div className="setting-field">
              <label htmlFor="model-type">Loại mô hình</label>
              <select
                id="model-type"
                value={input.model_type}
                onChange={(event) =>
                  setInput((current) => ({
                    ...current,
                    model_type: event.target.value,
                  }))
                }
                required
              >
                <option value="reading_region_ridge">Định vị vùng chỉ số</option>
                <option value="meter_locator_ridge">Định vị toàn bộ công tơ</option>
              </select>
            </div>
            <div className="setting-field">
              <label htmlFor="model-version">Phiên bản</label>
              <input
                id="model-version"
                value={input.version}
                onChange={(event) =>
                  setInput((current) => ({
                    ...current,
                    version: event.target.value,
                  }))
                }
                placeholder="1.0.0"
                required
              />
            </div>
            <div className="setting-field">
              <label htmlFor="model-file">
                Đường dẫn tương đối trong MODELS_ROOT
              </label>
              <input
                id="model-file"
                value={input.file_path}
                onChange={(event) =>
                  setInput((current) => ({
                    ...current,
                    file_path: event.target.value,
                  }))
                }
                placeholder="reading_region_ridge/v1/model.npz"
                required
              />
            </div>
            <div className="setting-field">
              <label htmlFor="model-sha">SHA-256</label>
              <input
                id="model-sha"
                minLength={64}
                maxLength={64}
                value={input.sha256}
                onChange={(event) =>
                  setInput((current) => ({
                    ...current,
                    sha256: event.target.value,
                  }))
                }
                required
              />
            </div>
            <div className="setting-field">
              <label htmlFor="model-metrics">JSON chỉ số đánh giá</label>
              <input
                id="model-metrics"
                value={metricsJson}
                onChange={(event) => setMetricsJson(event.target.value)}
                required
              />
            </div>
          </div>
          <button type="submit" disabled={saving}>
            {saving ? "Đang xác minh…" : "Xác minh và đăng ký"}
          </button>
          </fieldset>
        </form>
      </details>
    </section>
  );
}
