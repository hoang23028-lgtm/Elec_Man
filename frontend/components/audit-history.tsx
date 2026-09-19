"use client";

import { useEffect, useState } from "react";

import { getAuditLogs, type AuditRow } from "@/services/audit";

const pageSize = 10;
const actions = [
  "",
  "LOGIN_SUCCESS",
  "LOGIN_FAILED",
  "CREATE_BATCH",
  "UPLOAD_IMAGE",
  "START_BATCH",
  "CONFIRM_RESULT",
  "AUTO_CONFIRM_RESULT",
  "UPDATE_CONFIRMED_RESULT",
  "REJECT_RESULT",
  "EXPORT_EXCEL",
  "CHANGE_SETTING",
  "REGISTER_MODEL",
  "ACTIVATE_MODEL",
  "LOGOUT",
];
const actionLabels: Record<string, string> = {
  LOGIN_SUCCESS: "Đăng nhập thành công",
  LOGIN_FAILED: "Đăng nhập thất bại",
  CREATE_BATCH: "Tạo lô dữ liệu",
  UPLOAD_IMAGE: "Tải ảnh lên",
  START_BATCH: "Bắt đầu xử lý lô",
  CONFIRM_RESULT: "Xác nhận kết quả",
  AUTO_CONFIRM_RESULT: "AI tự động xác nhận",
  UPDATE_CONFIRMED_RESULT: "Cập nhật kết quả đã xác nhận",
  REJECT_RESULT: "Từ chối kết quả",
  EXPORT_EXCEL: "Xuất tệp Excel",
  CHANGE_SETTING: "Thay đổi cấu hình",
  REGISTER_MODEL: "Đăng ký mô hình",
  ACTIVATE_MODEL: "Kích hoạt mô hình",
  LOGOUT: "Đăng xuất",
};
const targetLabels: Record<string, string> = {
  user: "Người dùng",
  batch: "Lô dữ liệu",
  image: "Hình ảnh",
  model: "Mô hình",
  system_settings: "Cấu hình hệ thống",
};

function targetIdLabel(value: string | null): string {
  if (!value) return "";
  const bulkMatch = value.match(/^bulk:(\d+) settings$/);
  return bulkMatch ? `Thay đổi hàng loạt: ${bulkMatch[1]} cấu hình` : value;
}

export function AuditHistory() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setRows(await getAuditLogs(page * pageSize, pageSize, action));
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
                <th>Thời gian</th>
                <th>Hành động</th>
                <th>Người dùng</th>
                <th>Đối tượng</th>
                <th>Địa chỉ IP</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
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
        <span>Trang {page + 1}</span>
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => current + 1)}
          disabled={rows.length < pageSize || loading}
        >
          Sau
        </button>
      </nav>
    </section>
  );
}
