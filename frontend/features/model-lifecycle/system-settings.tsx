"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useLeaveGuard } from "@/hooks/use-leave-guard";

import {
  getSettings,
  saveSettings,
  type Setting,
} from "@/services/administration";

const labels: Record<string, string> = {
  confidence_ok_threshold: "Ngưỡng tin cậy đạt yêu cầu",
  confidence_review_threshold: "Ngưỡng tin cậy cần kiểm duyệt",
  max_upload_size_mb: "Dung lượng tải lên tối đa (MB)",
  max_retry_count: "Số lần thử lại tối đa",
  data_retention_days: "Thời gian lưu trữ dữ liệu (ngày)",
  worker_poll_interval_seconds: "Chu kỳ kiểm tra của tiến trình xử lý (giây)",
  training_auto_start: "Tự động huấn luyện (0: tắt, 1: bật)",
  training_min_samples: "Số mẫu tối thiểu để huấn luyện",
  training_min_new_samples: "Số mẫu mới để huấn luyện lại",
};
const descriptions: Record<string, string> = {
  confidence_ok_threshold:
    "Ngưỡng tham khảo; tự động xác nhận đang bị chặn cho đến khi có đánh giá độc lập. Thay đổi ngưỡng này không bật tự động xác nhận.",
  confidence_review_threshold:
    "Ngưỡng độ tin cậy dùng để ưu tiên kết quả cần kiểm duyệt thủ công.",
  max_upload_size_mb:
    "Chỉ đọc · MAX_IMAGE_SIZE_MB của backend. Sửa môi trường triển khai và tạo lại backend để thay đổi.",
  max_retry_count:
    "Chỉ đọc · MAX_RETRY_COUNT. Giữ môi trường backend và worker đồng nhất khi triển khai lại.",
  data_retention_days:
    "Thời gian dự kiến lưu trữ dữ liệu; hệ thống chưa bật xóa tự động.",
  worker_poll_interval_seconds:
    "Chỉ đọc · WORKER_POLL_INTERVAL_SECONDS trong môi trường backend. Worker cần cùng giá trị khi triển khai; đây không phải số đo trực tiếp từ worker.",
  training_auto_start:
    "Trainer tự tạo phiên mới khi dataset đủ điều kiện và có đủ mẫu mới.",
  training_min_samples:
    "Chỉ tính ảnh có số điện đúng, vùng toàn bộ công tơ và vùng dãy số đã được người dùng lưu nhãn; khuyến nghị tối thiểu 200 ảnh đa dạng.",
  training_min_new_samples:
    "Tránh huấn luyện lại liên tục khi dataset chỉ tăng một vài ảnh.",
};
const hiddenLegacySettings = new Set(["electricity_unit_price_vnd"]);

export function SystemSettings({ csrfToken }: { csrfToken: string }) {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  useLeaveGuard(settings.some((setting) => String(setting.value) !== drafts[setting.key]), saving, "lưu cấu hình hệ thống");

  async function load() {
    try {
      const rows = await getSettings();
      const visibleRows = rows.filter((row) => !hiddenLegacySettings.has(row.key));
      setSettings(visibleRows);
      setDrafts(
        Object.fromEntries(visibleRows.map((row) => [row.key, String(row.value)])),
      );
      setError(null);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể tải cấu hình.",
      );
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    const values = Object.fromEntries(
      settings.filter((setting) => setting.editable && String(setting.value) !== drafts[setting.key])
        .map((setting) => [setting.key, Number(drafts[setting.key])]),
    );
    if (!Object.keys(values).length) { setSaving(false); setNotice("Không có cấu hình thay đổi."); return; }
    if (Object.values(values).some((value) => !Number.isFinite(value))) {
      setError("Mọi cấu hình phải là một số hợp lệ.");
      setSaving(false);
      return;
    }
    try {
      const rows = await saveSettings(values, csrfToken);
      const visibleRows = rows.filter((row) => !hiddenLegacySettings.has(row.key));
      setSettings(visibleRows);
      setDrafts(Object.fromEntries(visibleRows.map((row) => [row.key, String(row.value)])));
      window.dispatchEvent(new Event("training-data-changed"));
      setNotice("Cấu hình đã được lưu và ghi vào lịch sử kiểm toán.");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể lưu cấu hình.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel full-span" aria-labelledby="settings-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Vòng đời mô hình</p>
          <h2 id="settings-title">Cấu hình hệ thống</h2>
        </div>
        <span className="badge">Mọi thay đổi đều được ghi nhận</span>
      </div>
      <p className="muted">
        Chính sách huấn luyện được lưu tập trung. Các trường triển khai là chỉ đọc,
        lấy từ môi trường backend; cần sửa môi trường và tạo lại dịch vụ để thay đổi.
      </p>
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
      {settings.length === 0 && !error ? (
        <p className="muted" role="status">
          Đang tải cấu hình…
        </p>
      ) : (
        <form className="settings-form" onSubmit={submit}>
          <div className="settings-grid">
            {settings.map((setting) => (
              <div className="setting-field" key={setting.key}>
                <label htmlFor={`setting-${setting.key}`}>
                  {labels[setting.key] ?? setting.key}
                </label>
                <input
                  id={`setting-${setting.key}`}
                  type="number"
                  disabled={saving || !setting.editable}
                  min={setting.key === "training_min_samples" ? 3 : 0}
                  max={setting.key.includes("confidence") || setting.key === "training_auto_start" ? 1 : undefined}
                  step={
                    setting.key.includes("confidence")
                      ? "0.01"
                      : setting.key.includes("seconds")
                        ? "0.1"
                        : "1"
                  }
                  value={drafts[setting.key] ?? ""}
                  onChange={(event) =>
                    setDrafts((current) => ({
                      ...current,
                      [setting.key]: event.target.value,
                    }))
                  }
                  required
                />
                <small>
                  {descriptions[setting.key] ?? setting.description}
                </small>
              </div>
            ))}
          </div>
          <button type="submit" disabled={saving}>
            {saving ? "Đang lưu cấu hình…" : "Lưu cấu hình"}
          </button>
        </form>
      )}
    </section>
  );
}
