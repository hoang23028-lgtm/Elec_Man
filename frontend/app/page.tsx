"use client";

import { useEffect, useRef, useState } from "react";
import { pages, isPageId, NavigationIcon, type PageId } from "@/features/app-shell/navigation";
import dynamic from "next/dynamic";

import { canLeavePage } from "@/hooks/use-leave-guard";
import { useAuthentication } from "@/features/auth/use-authentication";
import { AuthDialog } from "@/features/auth/auth-dialog";
import { DashboardSummary } from "@/features/dashboard/dashboard-summary";
import { SectionTabs } from "@/components/section-tabs";
import { canAccessPage, canOperate, roleLabels } from "@/types/auth";

const loadingPanel = () => (
  <section className="panel full-span" aria-busy="true">
    <p className="muted" role="status">Đang tải chức năng…</p>
  </section>
);
const BatchOverview = dynamic(
  () => import("@/features/batches/batch-overview").then((module) => module.BatchOverview),
  { loading: loadingPanel, ssr: false },
);
const FolderUpload = dynamic(
  () => import("@/features/operations/folder-upload").then((module) => module.FolderUpload),
  { loading: loadingPanel, ssr: false },
);
const AuditHistory = dynamic(
  () => import("@/features/traceability/audit-history").then((module) => module.AuditHistory),
  { loading: loadingPanel, ssr: false },
);
const ModelOperations = dynamic(
  () => import("@/features/model-lifecycle/model-operations").then((module) => module.ModelOperations),
  { loading: loadingPanel, ssr: false },
);
const SystemSettings = dynamic(
  () => import("@/features/model-lifecycle/system-settings").then((module) => module.SystemSettings),
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
const MonthlyReadingHistory = dynamic(
  () =>
    import("@/features/administration/monthly-reading-history").then(
      (module) => module.MonthlyReadingHistory,
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
const TrainingDataQuality = dynamic(
  () => import("@/features/model-lifecycle/training-data-quality").then((module) => module.TrainingDataQuality),
  { loading: loadingPanel, ssr: false },
);
const OperationalHealth = dynamic(
  () => import("@/features/model-lifecycle/operational-health").then((module) => module.OperationalHealth),
  { loading: loadingPanel, ssr: false },
);
const OperationsResults = dynamic(
  () =>
    import("@/features/operations/operations-results").then(
      (module) => module.OperationsResults,
    ),
  { loading: loadingPanel, ssr: false },
);

export default function HomePage() {
  const [activePage, setActivePage] = useState<PageId>("dashboard");
  const [operationsRefresh, setOperationsRefresh] = useState(0);
  const navScrollRef = useRef<HTMLDivElement>(null);
  const activeNavItemRef = useRef<HTMLButtonElement>(null);
  const auth = useAuthentication(() => setActivePage("dashboard"));
  const { message, error, csrfToken, authLoading, sessionExpired, sessionRole, loginOpen, setLoginOpen, setAuthMode, setShowPasswords, setError, loginTriggerRef, signOut } = auth;

  useEffect(() => {
    if (authLoading) return;
    function syncPageFromLocation() {
      const requested = window.location.hash.slice(1);
      const nextPage = isPageId(requested) ? requested : "dashboard";
      if (nextPage !== activePage && !canLeavePage()) {
        window.history.replaceState(null, "", `#${activePage}`);
        return;
      }
      if (!canAccessPage(csrfToken ? sessionRole : null, nextPage)) {
        setActivePage("dashboard");
        window.history.replaceState(null, "", "#dashboard");
        return;
      }
      setActivePage(nextPage);
    }

    syncPageFromLocation();
    window.addEventListener("hashchange", syncPageFromLocation);
    return () => window.removeEventListener("hashchange", syncPageFromLocation);
  }, [csrfToken, sessionRole, authLoading, activePage]);

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

  function navigate(page: PageId) {
    if (sessionExpired && page !== "dashboard") { setLoginOpen(true); return; }
    if (!canAccessPage(csrfToken ? sessionRole : null, page)) return;
    if (page !== activePage && !canLeavePage()) return;
    setActivePage(page);
    window.history.pushState(null, "", `#${page}`);
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: "auto" });
      document.getElementById("page-view-title")?.focus();
    });
  }

  const isAdmin = !!csrfToken && canOperate(sessionRole);
  const isSystemAdmin = !!csrfToken && sessionRole === "SUPER_ADMIN";
  const displayedPage = canAccessPage(csrfToken ? sessionRole : null, activePage) ? activePage : "dashboard";
  const currentPage =
    pages.find((page) => page.id === displayedPage) ?? pages[0];
  const availablePages = pages.filter((page) => canAccessPage(csrfToken ? sessionRole : null, page.id));

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
                  <span>Quản lý điện năng</span>
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
                <span className="admin-status">{sessionExpired ? "Phiên đã hết hạn" : sessionRole ? roleLabels[sessionRole] : "Người xem"}</span>
                {sessionExpired && <button type="button" onClick={() => setLoginOpen(true)}>Đăng nhập lại</button>}
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
                disabled={authLoading}
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
        <div className={`shell ${displayedPage === "operations" ? "operations-shell" : ""}`}>
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
                className={`page-context ${isAdmin ? "admin" : "public"}`}
              >
                {isSystemAdmin ? "Toàn hệ thống" : isAdmin ? "Nghiệp vụ vận hành" : csrfToken ? "Tài khoản · chỉ xem" : "Công khai · chỉ xem"}
              </span>
            </div>
            <div className={`workspace page-content ${displayedPage}-layout`} inert={sessionExpired && displayedPage !== "dashboard"}>
              {displayedPage === "dashboard" && (
                <DashboardSummary readOnly={!isAdmin} />
              )}
              {isAdmin && displayedPage === "operations" && (
                <>
                  <details className="operations-upload"><summary>Tải thêm ảnh công tơ</summary><FolderUpload
                    csrfToken={csrfToken}
                    onQueued={() => setOperationsRefresh((value) => value + 1)}
                  /></details>
                  <OperationsResults
                    csrfToken={csrfToken}
                    refreshKey={operationsRefresh}
                  />
                  <MonthlyExport csrfToken={csrfToken} />
                </>
              )}
              {isAdmin && displayedPage === "batches" && (
                <BatchOverview />
              )}
              {isAdmin && displayedPage === "administration" && (
                <SectionTabs label="Chức năng quản trị" items={[
                  { id: "customers", label: "Khách hàng", content: <CustomerDataManagement csrfToken={csrfToken} /> },
                  { id: "readings", label: "Chỉ số tháng", content: <MonthlyReadingHistory /> },
                  { id: "reports", label: "Báo cáo", content: <MonthlyExport csrfToken={csrfToken} /> },
                  ...(isSystemAdmin ? [{ id: "accounts", label: "Tài khoản", content: <AccountManagement csrfToken={csrfToken} /> }] : []),
                ]} />
              )}
              {isSystemAdmin && displayedPage === "model-lifecycle" && (
                <SectionTabs label="Vòng đời mô hình" items={[
                  { id: "data", label: "Dữ liệu huấn luyện", content: <TrainingDataQuality csrfToken={csrfToken} /> },
                  { id: "training", label: "Huấn luyện", content: <TrainingPipeline csrfToken={csrfToken} /> },
                  { id: "models", label: "Kho mô hình", content: <ModelOperations csrfToken={csrfToken} /> },
                  { id: "settings", label: "Cấu hình hệ thống", content: <SystemSettings csrfToken={csrfToken} /> },
                  { id: "health", label: "Giám sát", content: <OperationalHealth /> },
                ]} />
              )}
              {isSystemAdmin && displayedPage === "traceability" && (
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

      <AuthDialog auth={auth} />
    </>
  );
}
