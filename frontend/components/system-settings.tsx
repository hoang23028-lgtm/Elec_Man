"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

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
  electricity_unit_price_vnd: "Đơn giá điện tạm tính (VNĐ/kWh)",
  training_auto_start: "Tự động huấn luyện (0: tắt, 1: bật)",
  training_min_samples: "Số mẫu tối thiểu để huấn luyện",
  training_min_new_samples: "Số mẫu mới để huấn luyện lại",
};
const descriptions: Record<string, string> = {
  confidence_ok_threshold:
    "Độ tin cậy tối thiểu để mô hình sản xuất đề xuất tự động chấp nhận.",
  confidence_review_threshold:
    "Ngưỡng độ tin cậy dùng để ưu tiên kết quả cần kiểm duyệt thủ công.",
  max_upload_size_mb:
    "Giới hạn dung lượng tải lên trong vận hành; cấu hình môi trường có hiệu lực sau khi khởi động lại.",
  max_retry_count:
    "Số lần xử lý lại tối đa áp dụng cho tiến trình xử lý mới triển khai.",
  data_retention_days:
    "Thời gian dự kiến lưu trữ dữ liệu; hệ thống chưa bật xóa tự động.",
  worker_poll_interval_seconds:
    "Chu kỳ kiểm tra mong muốn, được áp dụng sau khi khởi động lại tiến trình xử lý.",
  electricity_unit_price_vnd:
    "Đơn giá bình quân dùng trên Dashboard để tạm tính; không thay thế hóa đơn chính thức.",
  training_auto_start:
    "Trainer tự tạo phiên mới khi dataset đủ điều kiện và có đủ mẫu mới.",
  training_min_samples:
    "Chỉ tính ảnh có mã khách hàng và số điện đã được con người xác nhận.",
  training_min_new_samples:
    "Tránh huấn luyện lại liên tục khi dataset chỉ tăng một vài ảnh.",
};

export function SystemSettings({ csrfToken }: { csrfToken: string }) {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    try {
      const rows = await getSettings();
      setSettings(rows);
      setDrafts(
        Object.fromEntries(rows.map((row) => [row.key, String(row.value)])),
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
      Object.entries(drafts).map(([key, value]) => [key, Number(value)]),
    );
    if (Object.values(values).some((value) => !Number.isFinite(value))) {
      setError("Mọi cấu hình phải là một số hợp lệ.");
      setSaving(false);
      return;
    }
    try {
      const rows = await saveSettings(values, csrfToken);
      setSettings(rows);
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
          <p className="eyebrow">Quản trị</p>
          <h2 id="settings-title">Cấu hình hệ thống</h2>
        </div>
        <span className="badge">Mọi thay đổi đều được ghi nhận</span>
      </div>
      <p className="muted">
        Các chính sách vận hành được lưu tập trung. Giới hạn ở cấp triển khai sẽ
        có hiệu lực sau khi dịch vụ liên quan được khởi động lại.
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
