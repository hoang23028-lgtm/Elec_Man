"use client";

import type { useAuthentication } from "./use-authentication";

export function AuthDialog({ auth }: { auth: ReturnType<typeof useAuthentication> }) {
  const { error, csrfToken, sessionExpired, loginOpen, authMode, showPasswords, setShowPasswords, loginModalRef, registerLogin, handleLoginSubmit, loginErrors, isLoggingIn, registerRegistration, handleRegistrationSubmit, registrationErrors, isRegistering, closeLogin, submitLogin, submitRegistration, switchAuthMode } = auth;
  return <>      {loginOpen && (!csrfToken || sessionExpired) && (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeLogin();
          }}
        >
          <section
            className="login-modal"
            role="dialog"
            ref={loginModalRef}
            aria-modal="true"
            aria-labelledby="login-title"
          >
            <div className="modal-heading">
              <div>
                <p className="eyebrow">Tài khoản hệ thống</p>
                <h2 id="login-title">
                  {authMode === "login" ? "Đăng nhập quản trị" : "Đăng ký tài khoản"}
                </h2>
              </div>
              <button
                className="modal-close secondary"
                type="button"
                onClick={closeLogin}
              >
                Đóng
              </button>
            </div>
            <div className="auth-tabs" role="group" aria-label="Chọn hình thức xác thực">
              <button
                type="button"
                aria-pressed={authMode === "login"}
                className={authMode === "login" ? "active" : ""}
                onClick={() => switchAuthMode("login")}
              >
                Đăng nhập
              </button>
              <button
                type="button"
                aria-pressed={authMode === "register"}
                className={authMode === "register" ? "active" : ""}
                onClick={() => switchAuthMode("register")}
              >
                Đăng ký
              </button>
            </div>
            {authMode === "login" ? (
              <>
                <p className="muted auth-description">
                  Đăng nhập để quản lý tải ảnh, kiểm duyệt, cấu hình hệ thống,
                  mô hình và nhật ký kiểm toán.
                </p>
                <form onSubmit={handleLoginSubmit(submitLogin)} noValidate>
              <label htmlFor="username">Tên đăng nhập</label>
              <input
                id="username"
                autoFocus
                autoComplete="username"
                aria-invalid={Boolean(loginErrors.username)}
                aria-describedby={loginErrors.username ? "login-username-error" : undefined}
                {...registerLogin("username", {
                  required: "Vui lòng nhập tên đăng nhập.",
                })}
              />
              {loginErrors.username?.message && (
                <span id="login-username-error" className="field-error">
                  {loginErrors.username.message}
                </span>
              )}
              <label htmlFor="password">Mật khẩu</label>
              <input
                id="password"
                type={showPasswords ? "text" : "password"}
                autoComplete="current-password"
                aria-invalid={Boolean(loginErrors.password)}
                aria-describedby={loginErrors.password ? "login-password-error" : undefined}
                {...registerLogin("password", {
                  required: "Vui lòng nhập mật khẩu.",
                })}
              />
              {loginErrors.password?.message && (
                <span id="login-password-error" className="field-error">
                  {loginErrors.password.message}
                </span>
              )}
              <label className="auth-password-toggle">
                <input
                  type="checkbox"
                  checked={showPasswords}
                  onChange={(event) => setShowPasswords(event.target.checked)}
                />
                <span>Hiện mật khẩu</span>
              </label>
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" disabled={isLoggingIn}>
                {isLoggingIn ? "Đang đăng nhập…" : "Đăng nhập quản trị"}
              </button>
            </form>
              </>
            ) : (
              <>
                <p className="muted auth-description">
                  Tài khoản mới sẽ ở trạng thái chờ. Quản trị viên phải kích
                  hoạt trước khi bạn có thể đăng nhập.
                </p>
                <form onSubmit={handleRegistrationSubmit(submitRegistration)} noValidate>
                  <label htmlFor="register-username">Tên đăng nhập</label>
                  <input
                    id="register-username"
                    autoFocus
                    autoComplete="username"
                    aria-invalid={Boolean(registrationErrors.username)}
                    aria-describedby={
                      registrationErrors.username
                        ? "register-username-error"
                        : "register-username-help"
                    }
                    {...registerRegistration("username", {
                      required: "Vui lòng nhập tên đăng nhập.",
                      minLength: { value: 3, message: "Tên đăng nhập cần ít nhất 3 ký tự." },
                      maxLength: { value: 64, message: "Tên đăng nhập không quá 64 ký tự." },
                      pattern: {
                        value: /^[A-Za-z0-9._-]+$/,
                        message: "Chỉ dùng chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang.",
                      },
                    })}
                  />
                  <span id="register-username-help" className="field-help">
                    Từ 3–64 ký tự; không dùng khoảng trắng hoặc chữ có dấu.
                  </span>
                  {registrationErrors.username?.message && (
                    <span id="register-username-error" className="field-error">
                      {registrationErrors.username.message}
                    </span>
                  )}

                  <label htmlFor="register-password">Mật khẩu</label>
                  <input
                    id="register-password"
                    type={showPasswords ? "text" : "password"}
                    autoComplete="new-password"
                    aria-invalid={Boolean(registrationErrors.password)}
                    aria-describedby={
                      registrationErrors.password
                        ? "register-password-error"
                        : "register-password-help"
                    }
                    {...registerRegistration("password", {
                      required: "Vui lòng nhập mật khẩu.",
                      minLength: { value: 12, message: "Mật khẩu cần ít nhất 12 ký tự." },
                      maxLength: { value: 256, message: "Mật khẩu không quá 256 ký tự." },
                    })}
                  />
                  <span id="register-password-help" className="field-help">
                    Dùng tối thiểu 12 ký tự. Có thể dán từ trình quản lý mật khẩu.
                  </span>
                  {registrationErrors.password?.message && (
                    <span id="register-password-error" className="field-error">
                      {registrationErrors.password.message}
                    </span>
                  )}

                  <label htmlFor="register-password-confirm">Nhập lại mật khẩu</label>
                  <input
                    id="register-password-confirm"
                    type={showPasswords ? "text" : "password"}
                    autoComplete="new-password"
                    aria-invalid={Boolean(registrationErrors.confirmPassword)}
                    aria-describedby={
                      registrationErrors.confirmPassword
                        ? "register-confirm-error"
                        : undefined
                    }
                    {...registerRegistration("confirmPassword", {
                      required: "Vui lòng nhập lại mật khẩu.",
                      validate: (value, values) =>
                        value === values.password || "Mật khẩu nhập lại chưa khớp.",
                    })}
                  />
                  {registrationErrors.confirmPassword?.message && (
                    <span id="register-confirm-error" className="field-error">
                      {registrationErrors.confirmPassword.message}
                    </span>
                  )}
                  <label className="auth-password-toggle">
                    <input
                      type="checkbox"
                      checked={showPasswords}
                      onChange={(event) => setShowPasswords(event.target.checked)}
                    />
                    <span>Hiện mật khẩu</span>
                  </label>
                  {error && (
                    <p className="error" role="alert">
                      {error}
                    </p>
                  )}
                  <button type="submit" disabled={isRegistering}>
                    {isRegistering ? "Đang gửi yêu cầu…" : "Gửi yêu cầu đăng ký"}
                  </button>
                </form>
              </>
            )}
          </section>
        </div>
      )}</>;
}
