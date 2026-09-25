"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import dynamic from "next/dynamic";

import { login, logout, registerAccount } from "@/services/auth";
import type { LoginInput, RegistrationFormInput } from "@/types/auth";
import { FolderUpload } from "@/components/folder-upload";
import { DashboardSummary } from "@/components/dashboard-summary";

const loadingPanel = () => (
  <section className="panel full-span" aria-busy="true">
    <p className="muted" role="status">Đang tải chức năng…</p>
  </section>
);
const BatchOverview = dynamic(
  () => import("@/components/batch-overview").then((module) => module.BatchOverview),
  { loading: loadingPanel, ssr: false },
);
const AuditHistory = dynamic(
  () => import("@/components/audit-history").then((module) => module.AuditHistory),
  { loading: loadingPanel, ssr: false },
);
const ModelOperations = dynamic(
  () => import("@/components/model-operations").then((module) => module.ModelOperations),
  { loading: loadingPanel, ssr: false },
);
const SystemSettings = dynamic(
  () => import("@/components/system-settings").then((module) => module.SystemSettings),
  { loading: loadingPanel, ssr: false },
);
const AccountManagement = dynamic(
  () =>
    import("@/features/administration/account-management").then(
      (module) => module.AccountManagement,
    ),
  { loading: loadingPanel, ssr: false },
);
const CustomerDataManagement = dynamic(
  () =>
    import("@/features/administration/customer-data-management").then(
      (module) => module.CustomerDataManagement,
    ),
  { loading: loadingPanel, ssr: false },
);
const MonthlyExport = dynamic(
  () =>
    import("@/features/administration/monthly-export").then(
      (module) => module.MonthlyExport,
    ),
  { loading: loadingPanel, ssr: false },
);
const TrainingPipeline = dynamic(
  () =>
    import("@/features/model-lifecycle/training-pipeline").then(
      (module) => module.TrainingPipeline,
    ),
  { loading: loadingPanel, ssr: false },
);
const OperationsResults = dynamic(
  () =>
    import("@/components/operations-results").then(
      (module) => module.OperationsResults,
    ),
  { loading: loadingPanel, ssr: false },
);

const pages = [
  {
    id: "dashboard",
    label: "Tổng quan",
    eyebrow: "Tổng quan",
    title: "Bảng điều khiển vận hành",
    description: "Theo dõi khối lượng xử lý và tình trạng chung của hệ thống.",
  },
  {
    id: "operations",
    label: "Vận hành",
    eyebrow: "Xử lý hình ảnh",
    title: "Tải ảnh và vận hành dữ liệu",
    description:
      "Tạo lô dữ liệu, tải ảnh đồng hồ điện và theo dõi tiến trình OCR.",
  },
  {
    id: "batches",
    label: "Các lô dữ liệu",
    eyebrow: "Lịch sử xử lý",
    title: "Các lô dữ liệu",
    description:
      "Theo dõi từng lô và chi tiết hình ảnh, kết quả OCR cùng trạng thái xử lý.",
  },
  {
    id: "administration",
    label: "Quản trị",
    eyebrow: "Chính sách hệ thống",
    title: "Quản trị hệ thống",
    description:
      "Quản lý tài khoản, mật khẩu, ngưỡng vận hành và chính sách hệ thống.",
  },
  {
    id: "model-lifecycle",
    label: "Vòng đời mô hình",
    eyebrow: "Quản trị AI",
    title: "Vòng đời mô hình",
    description:
      "Đánh giá, đăng ký, xác minh và kích hoạt các gói mô hình được kiểm soát.",
  },
  {
    id: "traceability",
    label: "Truy vết",
    eyebrow: "Nhật ký kiểm toán",
    title: "Truy vết hoạt động",
    description: "Xem lại các sự kiện bảo mật và vận hành trong toàn hệ thống.",
  },
] as const;

type PageId = (typeof pages)[number]["id"];

function isPageId(value: string): value is PageId {
  return pages.some((page) => page.id === value);
}

function NavigationIcon({ page }: { page: PageId }) {
  const paths: Record<PageId, ReactNode> = {
    dashboard: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    operations: (
      <>
        <path d="M12 3v12" />
        <path d="m7 8 5-5 5 5" />
        <path d="M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" />
      </>
    ),
    batches: (
      <>
        <path d="M3 7h7l2 2h9v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
        <path d="M3 7V5a2 2 0 0 1 2-2h5l2 2h5" />
      </>
    ),
    administration: (
      <>
        <path d="M4 6h16" />
        <path d="M4 12h16" />
        <path d="M4 18h16" />
        <circle cx="8" cy="6" r="2" />
        <circle cx="16" cy="12" r="2" />
        <circle cx="10" cy="18" r="2" />
      </>
    ),
    "model-lifecycle": (
      <>
        <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
        <path d="m4.5 7.5 7.5 4 7.5-4" />
        <path d="M12 11.5V21" />
      </>
    ),
    traceability: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
        <path d="M7 3 4 6" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      className="nav-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[page]}
    </svg>
  );
}

export default function HomePage() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [showPasswords, setShowPasswords] = useState(false);
  const [activePage, setActivePage] = useState<PageId>("dashboard");
  const [operationsRefresh, setOperationsRefresh] = useState(0);
  const navScrollRef = useRef<HTMLDivElement>(null);
  const activeNavItemRef = useRef<HTMLButtonElement>(null);
  const loginTriggerRef = useRef<HTMLButtonElement>(null);
  const loginModalRef = useRef<HTMLElement>(null);
  const loginForm = useForm<LoginInput>();
  const registrationForm = useForm<RegistrationFormInput>();
  const {
    register: registerLogin,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors, isSubmitting: isLoggingIn },
  } = loginForm;
  const {
    register: registerRegistration,
    handleSubmit: handleRegistrationSubmit,
    reset: resetRegistration,
    formState: { errors: registrationErrors, isSubmitting: isRegistering },
  } = registrationForm;

  const closeLogin = useCallback(() => {
    setLoginOpen(false);
    setAuthMode("login");
    setShowPasswords(false);
    setError(null);
    window.requestAnimationFrame(() => loginTriggerRef.current?.focus());
  }, []);

  useEffect(() => {
    function syncPageFromLocation() {
      const requested = window.location.hash.slice(1);
      const nextPage = isPageId(requested) ? requested : "dashboard";
      if (!csrfToken && nextPage !== "dashboard") {
        setActivePage("dashboard");
        window.history.replaceState(null, "", "#dashboard");
        return;
      }
      setActivePage(nextPage);
    }

    syncPageFromLocation();
    window.addEventListener("hashchange", syncPageFromLocation);
    return () => window.removeEventListener("hashchange", syncPageFromLocation);
  }, [csrfToken]);

  useEffect(() => {
    if (!loginOpen) return;
    function handleModalKeyboard(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeLogin();
        return;
      }
      if (event.key !== "Tab") return;
      const controls = loginModalRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      );
      if (!controls?.length) return;
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", handleModalKeyboard);
    return () => window.removeEventListener("keydown", handleModalKeyboard);
  }, [closeLogin, loginOpen]);

  useEffect(() => {
    const nav = navScrollRef.current;
    if (!nav) return;

    function centerActiveItem() {
      const item = activeNavItemRef.current;
      if (!item) return;
      nav?.scrollTo({
        left: item.offsetLeft - (nav.clientWidth - item.offsetWidth) / 2,
        behavior: "auto",
      });
    }

    centerActiveItem();
    const observer = new ResizeObserver(centerActiveItem);
    observer.observe(nav);
    return () => observer.disconnect();
  }, [activePage, csrfToken]);

  async function submitLogin(values: LoginInput) {
    setError(null);
    setMessage(null);
    try {
      const result = await login(values);
      // This value is not a credential. It remains only in React memory for
      // future state-changing requests and is never written to localStorage.
      setCsrfToken(result.csrf_token);
      setLoginOpen(false);
      setActivePage("dashboard");
      window.history.replaceState(null, "", "#dashboard");
      setMessage(
        "Đăng nhập thành công. Hãy tải ảnh, theo dõi lô dữ liệu và kiểm duyệt từng chỉ số.",
      );
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể đăng nhập.",
      );
    }
  }

  async function submitRegistration(values: RegistrationFormInput) {
    setError(null);
    setMessage(null);
    try {
      const result = await registerAccount({
        username: values.username,
        password: values.password,
      });
      setLoginOpen(false);
      setAuthMode("login");
      setMessage(result.message);
      window.requestAnimationFrame(() => document.getElementById("auth-trigger")?.focus());
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể gửi yêu cầu đăng ký.",
      );
    }
  }

  async function signOut() {
    if (!csrfToken) return;
    try {
      await logout(csrfToken);
      setCsrfToken(null);
      setLoginOpen(false);
      setActivePage("dashboard");
      window.history.replaceState(null, "", window.location.pathname);
      setMessage("Đã đăng xuất.");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể đăng xuất.",
      );
    }
  }

  function switchAuthMode(mode: "login" | "register") {
    if (mode === "register") resetRegistration();
    setAuthMode(mode);
    setShowPasswords(false);
    setError(null);
  }

  function navigate(page: PageId) {
    if (!csrfToken && page !== "dashboard") return;
    setActivePage(page);
    window.history.pushState(null, "", `#${page}`);
    window.requestAnimationFrame(() => {
      document.getElementById("page-view-title")?.focus();
    });
  }

  const displayedPage = csrfToken ? activePage : "dashboard";
  const currentPage =
    pages.find((page) => page.id === displayedPage) ?? pages[0];
  const availablePages = csrfToken ? pages : pages.slice(0, 1);

  return (
    <>
      <a className="skip-link" href="#main-content">
        Chuyển đến nội dung chính
      </a>
      <header className="app-navbar">
        <div className="navbar-inner">
          <div className="navbar-brand" aria-label="AI Quản lý đồng hồ điện">
            <span className="brand-mark">
              <NavigationIcon page="dashboard" />
            </span>
            <div>
              <h1>AI Đồng hồ điện</h1>
              <span>Trung tâm vận hành</span>
            </div>
          </div>
          <nav className="app-nav" aria-label="Điều hướng chính">
            <div className="nav-scroll" ref={navScrollRef}>
              {availablePages.map((page) => (
                <button
                  className="nav-item"
                  type="button"
                  key={page.id}
                  ref={displayedPage === page.id ? activeNavItemRef : null}
                  aria-current={displayedPage === page.id ? "page" : undefined}
                  onClick={() => navigate(page.id)}
                >
                  <NavigationIcon page={page.id} />
                  <span>{page.label}</span>
                </button>
              ))}
            </div>
          </nav>
          <div className="navbar-account">
            {csrfToken ? (
              <>
                <span className="admin-status">Quản trị viên</span>
                <button
                  className="navbar-action secondary"
                  type="button"
                  onClick={() => void signOut()}
                >
                  Đăng xuất
                </button>
              </>
            ) : (
              <button
                className="navbar-action"
                type="button"
                id="auth-trigger"
                ref={loginTriggerRef}
                onClick={() => {
                  setError(null);
                  setAuthMode("login");
                  setShowPasswords(false);
                  setLoginOpen(true);
                }}
              >
                Đăng nhập / Đăng ký
              </button>
            )}
          </div>
        </div>
      </header>

      <main id="main-content" className="app-main">
        <div className="shell">
          <section className="page-view" aria-labelledby="page-view-title">
            <div className="page-intro">
              <div>
                <p className="eyebrow">{currentPage.eyebrow}</p>
                <h2 id="page-view-title" tabIndex={-1}>
                  {currentPage.title}
                </h2>
                <p className="muted">{currentPage.description}</p>
              </div>
              <span
                className={`page-context ${csrfToken ? "admin" : "public"}`}
              >
                {csrfToken ? "Không gian quản trị" : "Công khai · chỉ xem"}
              </span>
            </div>
            <div className={`workspace page-content ${displayedPage}-layout`}>
              {displayedPage === "dashboard" && (
                <DashboardSummary csrfToken={csrfToken ?? undefined} />
              )}
              {csrfToken && displayedPage === "operations" && (
                <>
                  <FolderUpload
                    csrfToken={csrfToken}
                    onQueued={() => setOperationsRefresh((value) => value + 1)}
                  />
                  <OperationsResults
                    csrfToken={csrfToken}
                    refreshKey={operationsRefresh}
                  />
                </>
              )}
              {csrfToken && displayedPage === "batches" && (
                <BatchOverview />
              )}
              {csrfToken && displayedPage === "administration" && (
                <>
                  <MonthlyExport csrfToken={csrfToken} />
                  <CustomerDataManagement csrfToken={csrfToken} />
                  <AccountManagement csrfToken={csrfToken} />
                  <SystemSettings csrfToken={csrfToken} />
                </>
              )}
              {csrfToken && displayedPage === "model-lifecycle" && (
                <>
                  <TrainingPipeline csrfToken={csrfToken} />
                  <ModelOperations csrfToken={csrfToken} />
                </>
              )}
              {csrfToken && displayedPage === "traceability" && (
                <AuditHistory />
              )}
            </div>
          </section>
          {error && !loginOpen && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {message && (
            <p className="notice" role="status">
              {message}
            </p>
          )}
        </div>
      </main>

      {loginOpen && !csrfToken && (
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
      )}
    </>
  );
}
