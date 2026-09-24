"use client";

import { useEffect, useState } from "react";

import { getAuditLogsPage, type AuditRow } from "@/services/audit";

const pageSize = 10;
const actions = [
  "",
  "LOGIN_SUCCESS",
  "LOGIN_FAILED",
  "CREATE_BATCH",
  "UPLOAD_IMAGE",
  "START_BATCH",
  "PROCESSING_COMPLETED",
  "PROCESSING_RETRY_SCHEDULED",
  "PROCESSING_FAILED",
  "CONFIRM_RESULT",
  "AUTO_CONFIRM_RESULT",
  "UPDATE_CONFIRMED_RESULT",
  "REJECT_RESULT",
  "EXPORT_RECONCILIATION_REPORT",
  "IMPORT_CUSTOMERS",
  "CHANGE_SETTING",
  "REGISTER_MODEL",
  "ACTIVATE_MODEL",
  "TRAINING_QUEUED",
  "TRAINING_STARTED",
  "TRAINING_STAGE_CHANGED",
  "TRAINING_COMPLETED",
  "TRAINING_FAILED",
  "USER_CREATE",
  "USER_UPDATE",
  "USER_PASSWORD_CHANGE",
  "USER_DELETE",
  "LOGOUT",
];
const actionLabels: Record<string, string> = {
  LOGIN_SUCCESS: "Đăng nhập thành công",
  LOGIN_FAILED: "Đăng nhập thất bại",
  CREATE_BATCH: "Tạo lô dữ liệu",
  UPLOAD_IMAGE: "Tải ảnh lên",
  START_BATCH: "Bắt đầu xử lý lô",
  PROCESSING_COMPLETED: "Xử lý ảnh hoàn tất",
  PROCESSING_RETRY_SCHEDULED: "Lên lịch xử lý lại",
  PROCESSING_FAILED: "Xử lý ảnh thất bại",
  CONFIRM_RESULT: "Xác nhận kết quả",
  AUTO_CONFIRM_RESULT: "AI tự động xác nhận",
  UPDATE_CONFIRMED_RESULT: "Cập nhật kết quả đã xác nhận",
  REJECT_RESULT: "Từ chối kết quả",
  EXPORT_RECONCILIATION_REPORT: "Xuất báo cáo đối chiếu",
  IMPORT_CUSTOMERS: "Nhập dữ liệu khách hàng",
  CHANGE_SETTING: "Thay đổi cấu hình",
  REGISTER_MODEL: "Đăng ký mô hình",
  ACTIVATE_MODEL: "Kích hoạt mô hình",
  TRAINING_QUEUED: "Xếp hàng huấn luyện",
  TRAINING_STARTED: "Bắt đầu huấn luyện",
  TRAINING_STAGE_CHANGED: "Chuyển giai đoạn huấn luyện",
  TRAINING_COMPLETED: "Huấn luyện hoàn tất",
  TRAINING_FAILED: "Huấn luyện thất bại",
  USER_CREATE: "Tạo tài khoản",
  USER_UPDATE: "Cập nhật tài khoản",
  USER_PASSWORD_CHANGE: "Đổi mật khẩu tài khoản",
  USER_DELETE: "Xóa tài khoản",
  LOGOUT: "Đăng xuất",
};
const targetLabels: Record<string, string> = {
  user: "Người dùng",
  batch: "Lô dữ liệu",
  image: "Hình ảnh",
  model: "Mô hình",
  training_run: "Phiên huấn luyện",
  system_settings: "Cấu hình hệ thống",
  customer: "Khách hàng",
  export: "Báo cáo xuất",
};

const detailLabels: Record<string, string> = {
  trigger: "Nguồn khởi chạy",
  sample_count: "Tổng số mẫu",
  minimum_samples: "Số mẫu tối thiểu",
  new_samples_since_last_run: "Mẫu mới từ lần train trước",
  auto_start_enabled: "Tự động huấn luyện",
  stage: "Giai đoạn",
  last_stage: "Giai đoạn cuối",
  progress: "Tiến độ",
  training_count: "Mẫu huấn luyện",
  validation_count: "Mẫu validation",
  dataset_hash: "Checksum dataset",
  model_id: "Mã mô hình",
  model_name: "Tên mô hình",
  model_type: "Loại mô hình",
  model_version: "Phiên bản mô hình",
  version: "Phiên bản",
  model_sha256: "Checksum mô hình",
  sha256: "SHA-256",
  metrics: "Chỉ số đánh giá",
  previous_status: "Trạng thái trước",
  new_status: "Trạng thái mới",
  error_type: "Loại lỗi",
  error_message: "Nội dung lỗi",
  reason: "Lý do",
  batch_code: "Mã lô",
  batch_id: "Mã lô",
  ai_result_id: "Mã kết quả AI",
  confidence: "Độ tin cậy",
  threshold: "Ngưỡng áp dụng",
  correction_count: "Số trường chỉnh sửa",
  changed_fields: "Các trường đã thay đổi",
  review_action: "Thao tác kiểm duyệt",
  ai_customer_id: "Mã khách hàng AI nhận diện",
  ai_meter_reading: "Số điện AI nhận diện",
  customer_id_before: "Mã khách hàng trước thay đổi",
  customer_id_after: "Mã khách hàng sau thay đổi",
  meter_reading_before: "Số điện trước thay đổi",
  meter_reading_after: "Số điện sau thay đổi",
  folder_name: "Tên thư mục",
  status: "Trạng thái",
  original_filename: "Tên ảnh gốc",
  mime_type: "Loại tệp",
  file_size_bytes: "Kích thước (byte)",
  width: "Chiều rộng",
  height: "Chiều cao",
  job_count: "Số tác vụ",
  processor: "Bộ xử lý",
  max_attempts: "Số lần thử tối đa",
  job_id: "Mã tác vụ",
  processing_time_ms: "Thời gian xử lý (ms)",
  auto_confirmed: "Tự động xác nhận",
  error_code: "Mã lỗi",
  attempt_count: "Lần thử hiện tại",
  next_retry_at: "Thời điểm thử lại",
  customer_id: "Mã khách hàng",
  meter_reading: "Số điện",
  filename: "Tên tệp",
  exported_rows: "Số dòng đã xuất",
  excel_filename: "Tên tệp Excel",
  json_filename: "Tên tệp JSON",
  total: "Tổng số bản ghi",
  created: "Số bản ghi thêm mới",
  updated: "Số bản ghi cập nhật",
  reconciled_readings: "Kết quả đã đối chiếu lại",
  customer_match_status: "Trạng thái đối chiếu",
  matched_customer_id: "Khách hàng đã khớp",
  result: "Kết quả",
  session_expires_at: "Phiên hết hạn lúc",
  session_id: "Mã phiên đăng nhập",
  username: "Tên đăng nhập",
  is_active: "Trạng thái hoạt động",
};

function formatDetailValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(formatDetailValue).join(", ");
  if (typeof value === "object") {
    const change = value as { old?: unknown; new?: unknown };
    if ("old" in change || "new" in change) {
      return `${formatDetailValue(change.old)} → ${formatDetailValue(change.new)}`;
    }
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function AuditDetails({ details }: { details: Record<string, unknown> }) {
  const entries = Object.entries(details);
  if (!entries.length) return <>—</>;
  const changes = [
    {
      key: "customer_id",
      label: "Mã khách hàng",
      before: details.customer_id_before,
      after: details.customer_id_after,
    },
    {
      key: "meter_reading",
      label: "Số điện",
      before: details.meter_reading_before,
      after: details.meter_reading_after,
    },
  ].filter(
    (change) =>
      (change.before !== undefined || change.after !== undefined) &&
      change.before !== change.after,
  );
  const changeKeys = new Set([
    "customer_id_before",
    "customer_id_after",
    "meter_reading_before",
    "meter_reading_after",
  ]);
  const metadataEntries = entries.filter(([key]) => !changeKeys.has(key));
  return (
    <details className="audit-details">
      <summary>
        {changes.length
          ? `${changes.length} thay đổi thủ công · Xem chi tiết`
          : `${entries.length} thông tin · Xem chi tiết`}
      </summary>
      {changes.length > 0 && (
        <div className="audit-change-list" aria-label="Giá trị trước và sau thay đổi">
          {changes.map((change) => (
            <div className="audit-change" key={change.key}>
              <strong>{change.label}</strong>
              <span><small>Trước</small>{formatDetailValue(change.before)}</span>
              <b aria-hidden="true">→</b>
              <span><small>Sau</small>{formatDetailValue(change.after)}</span>
            </div>
          ))}
        </div>
      )}
      <dl>
        {metadataEntries.map(([key, value]) => (
          <div key={key}>
            <dt>{detailLabels[key] ?? key}</dt>
            <dd>{formatDetailValue(value)}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function targetIdLabel(value: string | null): string {
  if (!value) return "";
  const bulkMatch = value.match(/^bulk:(\d+) settings$/);
  return bulkMatch ? `Thay đổi hàng loạt: ${bulkMatch[1]} cấu hình` : value;
}

export function AuditHistory() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [total, setTotal] = useState(0);
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const result = await getAuditLogsPage(page * pageSize, pageSize, action);
      setRows(result.items);
      setTotal(result.total);
      setError(null);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể tải lịch sử kiểm toán.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [action, page]);

  return (
    <section className="panel full-span" aria-labelledby="audit-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Truy vết</p>
          <h2 id="audit-title">Lịch sử kiểm toán</h2>
        </div>
        <button
          className="secondary"
          type="button"
          onClick={() => void load()}
          disabled={loading}
        >
          Làm mới
        </button>
      </div>
      <div className="audit-filter">
        <label htmlFor="audit-action">Hành động</label>
        <select
          id="audit-action"
          value={action}
          onChange={(event) => {
            setPage(0);
            setAction(event.target.value);
          }}
        >
          {actions.map((item) => (
            <option key={item || "ALL"} value={item}>
              {item ? (actionLabels[item] ?? item) : "Tất cả hành động"}
            </option>
          ))}
        </select>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p className="muted" role="status">
          Đang tải lịch sử kiểm toán…
        </p>
      ) : rows.length === 0 ? (
        <p className="muted">Không có sự kiện nào phù hợp với bộ lọc.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="row-number">STT</th>
                <th>Thời gian</th>
                <th>Hành động</th>
                <th>Người dùng</th>
                <th>Đối tượng</th>
                <th>Chi tiết hành động</th>
                <th>Địa chỉ IP</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id}>
                  <td className="row-number">{page * pageSize + index + 1}</td>
                  <td>{new Date(row.created_at).toLocaleString("vi-VN")}</td>
                  <td>
                    <span className="badge">
                      {actionLabels[row.action] ?? row.action}
                    </span>
                  </td>
                  <td>{row.username ?? "Hệ thống"}</td>
                  <td>
                    {row.target_type
                      ? (targetLabels[row.target_type] ?? row.target_type)
                      : "—"}
                    <small>{targetIdLabel(row.target_id)}</small>
                  </td>
                  <td><AuditDetails details={row.details} /></td>
                  <td>{row.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav className="pagination" aria-label="Phân trang lịch sử kiểm toán">
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => Math.max(0, current - 1))}
          disabled={page === 0 || loading}
        >
          Trước
        </button>
        <span>
          Trang {page + 1} / {Math.max(1, Math.ceil(total / pageSize))}
        </span>
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => current + 1)}
          disabled={page + 1 >= Math.max(1, Math.ceil(total / pageSize)) || loading}
        >
          Sau
        </button>
      </nav>
    </section>
  );
}
