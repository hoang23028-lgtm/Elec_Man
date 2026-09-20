"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  changeUserPassword,
  createUser,
  deleteUser,
  getUsers,
  updateUser,
} from "@/features/administration/api";
import type { UserAccount } from "@/features/administration/types";
import { getCurrentUser } from "@/services/auth";

const PAGE_SIZE = 10;
type Editor =
  | { mode: "create" }
  | { mode: "edit"; user: UserAccount }
  | { mode: "password"; user: UserAccount }
  | null;

const formatDate = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "Chưa đăng nhập";

export function AccountManagement({ csrfToken }: { csrfToken: string }) {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [currentUserId, setCurrentUserId] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [editor, setEditor] = useState<Editor>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [result, current] = await Promise.all([
        getUsers((page - 1) * PAGE_SIZE, PAGE_SIZE, search),
        getCurrentUser(),
      ]);
      setUsers(result.items);
      setTotal(result.total);
      setCurrentUserId(current.id);
      setError(null);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể tải danh sách tài khoản.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    void load();
  }, [load]);

  function openEditor(next: Editor) {
    setEditor(next);
    setError(null);
    setNotice(null);
    setPassword("");
    setConfirmPassword("");
    if (next?.mode === "edit") {
      setUsername(next.user.username);
      setIsActive(next.user.is_active);
    } else {
      setUsername("");
      setIsActive(true);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor) return;
    if ((editor.mode === "create" || editor.mode === "password") && password.length < 12) {
      setError("Mật khẩu phải có ít nhất 12 ký tự.");
      return;
    }
    if ((editor.mode === "create" || editor.mode === "password") && password !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (editor.mode === "create") {
        await createUser({ username, password, is_active: isActive }, csrfToken);
        setNotice(`Đã tạo tài khoản ${username}.`);
      } else if (editor.mode === "edit") {
        await updateUser(
          editor.user.id,
          { username, is_active: isActive },
          csrfToken,
        );
        setNotice(`Đã cập nhật tài khoản ${username}.`);
      } else {
        await changeUserPassword(editor.user.id, password, csrfToken);
        setNotice(`Đã đổi mật khẩu cho ${editor.user.username}.`);
      }
      setEditor(null);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Thao tác thất bại.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(user: UserAccount) {
    if (
      !window.confirm(
        `Xóa tài khoản ${user.username}? Tài khoản sẽ bị khóa, các phiên đăng nhập bị thu hồi và lịch sử vẫn được giữ lại.`,
      )
    )
      return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await deleteUser(user.id, csrfToken);
      setNotice(`Đã xóa tài khoản ${user.username}.`);
      if (users.length === 1 && page > 1) setPage((value) => value - 1);
      else await load();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể xóa tài khoản.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel full-span" aria-labelledby="accounts-title">
      <div className="section-heading account-heading">
        <div>
          <p className="eyebrow">Quản trị truy cập</p>
          <h2 id="accounts-title">Quản lý tài khoản</h2>
          <p className="muted">
            Thêm, chỉnh sửa, khóa, đổi mật khẩu hoặc xóa mềm tài khoản quản trị.
            Mọi thao tác đều được ghi vào nhật ký truy vết.
          </p>
        </div>
        <button type="button" onClick={() => openEditor({ mode: "create" })}>
          Thêm tài khoản
        </button>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}

      {editor && (
        <form className="account-editor" onSubmit={submit}>
          <div className="account-editor-heading">
            <div>
              <p className="eyebrow">Thao tác tài khoản</p>
              <h3>
                {editor.mode === "create"
                  ? "Thêm tài khoản mới"
                  : editor.mode === "edit"
                    ? `Chỉnh sửa ${editor.user.username}`
                    : `Đổi mật khẩu cho ${editor.user.username}`}
              </h3>
            </div>
            <button className="secondary" type="button" onClick={() => setEditor(null)}>
              Hủy
            </button>
          </div>
          {editor.mode !== "password" && (
            <div className="account-form-grid">
              <label>
                Tên đăng nhập
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  minLength={3}
                  maxLength={64}
                  pattern="[A-Za-z0-9._-]+"
                  autoComplete="username"
                  required
                />
                <small>3–64 ký tự: chữ, số, dấu chấm, gạch ngang hoặc gạch dưới.</small>
              </label>
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={isActive}
                  disabled={editor.mode === "edit" && editor.user.id === currentUserId}
                  onChange={(event) => setIsActive(event.target.checked)}
                />
                Tài khoản đang hoạt động
              </label>
            </div>
          )}
          {(editor.mode === "create" || editor.mode === "password") && (
            <div className="account-form-grid">
              <label>
                Mật khẩu mới
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={12}
                  maxLength={256}
                  autoComplete="new-password"
                  required
                />
                <small>Tối thiểu 12 ký tự; có thể dán từ trình quản lý mật khẩu.</small>
              </label>
              <label>
                Xác nhận mật khẩu
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  minLength={12}
                  maxLength={256}
                  autoComplete="new-password"
                  required
                />
              </label>
            </div>
          )}
          <button type="submit" disabled={busy}>
            {busy ? "Đang lưu…" : "Lưu thay đổi"}
          </button>
        </form>
      )}

      <form
        className="account-search"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setSearch(searchInput.trim());
        }}
      >
        <label htmlFor="account-search">Tìm theo tên đăng nhập</label>
        <div className="inline-controls">
          <input
            id="account-search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Ví dụ: admin_operator"
          />
          <button type="submit">Tìm kiếm</button>
        </div>
      </form>

      {loading ? (
        <p className="muted" role="status">Đang tải tài khoản…</p>
      ) : users.length === 0 ? (
        <p className="empty-state">Không tìm thấy tài khoản phù hợp.</p>
      ) : (
        <div className="table-wrap account-table">
          <table>
            <thead>
              <tr>
                <th className="row-number">STT</th>
                <th>Tên đăng nhập</th>
                <th>Trạng thái</th>
                <th>Đăng nhập gần nhất</th>
                <th>Ngày tạo</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user, index) => (
                <tr key={user.id}>
                  <td className="row-number">{(page - 1) * PAGE_SIZE + index + 1}</td>
                  <td>
                    <strong>{user.username}</strong>
                    {user.id === currentUserId && <small>Tài khoản hiện tại</small>}
                  </td>
                  <td>
                    <span className={`badge ${user.is_active ? "success" : "warning"}`}>
                      {user.is_active ? "Đang hoạt động" : "Đã khóa"}
                    </span>
                  </td>
                  <td>{formatDate(user.last_login_at)}</td>
                  <td>{formatDate(user.created_at)}</td>
                  <td className="account-actions">
                    <button className="secondary" type="button" onClick={() => openEditor({ mode: "edit", user })}>
                      Sửa
                    </button>
                    <button className="secondary" type="button" onClick={() => openEditor({ mode: "password", user })}>
                      Đổi mật khẩu
                    </button>
                    <button className="danger" type="button" disabled={busy || user.id === currentUserId} onClick={() => void remove(user)}>
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="pagination">
        <button className="secondary" type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>
          Trang trước
        </button>
        <span>Trang {page} / {totalPages} · {total} tài khoản</span>
        <button className="secondary" type="button" disabled={page >= totalPages || loading} onClick={() => setPage((value) => value + 1)}>
          Trang sau
        </button>
      </div>
    </section>
  );
}
