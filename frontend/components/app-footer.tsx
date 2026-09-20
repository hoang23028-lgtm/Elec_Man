export function AppFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="app-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="footer-mark" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="4" y="3" width="16" height="18" rx="3" />
              <path d="M8 8h8" />
              <path d="M8 12h3" />
              <path d="M14 12h2" />
              <path d="M8 16h8" />
            </svg>
          </span>
          <div>
            <strong>Đồng hồ điện</strong>
            <p>Nhận diện, kiểm duyệt và truy vết chỉ số công tơ.</p>
          </div>
        </div>
        <div className="footer-meta">
          <span>Hệ thống vận hành</span>
          <span>© {currentYear} Quản lý đồng hồ điện</span>
        </div>
      </div>
    </footer>
  );
}
