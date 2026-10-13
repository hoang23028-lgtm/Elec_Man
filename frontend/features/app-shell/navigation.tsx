import type { ReactNode } from "react";

export const pages = [
  {
    id: "dashboard",
    label: "Tổng quan",
    eyebrow: "Tổng quan",
    title: "Tổng quan điện năng",
    description: "Theo dõi chỉ số đã xác nhận, mức tiêu thụ và tiền điện theo kỳ.",
  },
  {
    id: "operations",
    label: "Vận hành",
    eyebrow: "Xử lý hình ảnh",
    title: "Không gian xử lý công tơ",
    description:
      "Tải ảnh → kiểm tra vùng và chỉ số → xác nhận dữ liệu chính thức.",
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
    eyebrow: "Dữ liệu nghiệp vụ",
    title: "Khách hàng & báo cáo",
    description:
      "Quản lý hồ sơ khách hàng, tra cứu chỉ số tháng và xuất báo cáo.",
  },
  {
    id: "model-lifecycle",
    label: "Vòng đời mô hình",
    eyebrow: "Quản trị AI",
    title: "Vòng đời mô hình",
    description:
      "Cấu hình chính sách AI, huấn luyện, đánh giá và kích hoạt các gói mô hình.",
  },
  {
    id: "traceability",
    label: "Truy vết",
    eyebrow: "Nhật ký kiểm toán",
    title: "Truy vết hoạt động",
    description: "Xem lại các sự kiện bảo mật và vận hành trong toàn hệ thống.",
  },
] as const;

export type PageId = (typeof pages)[number]["id"];

export function isPageId(value: string): value is PageId {
  return pages.some((page) => page.id === value);
}

export function NavigationIcon({ page }: { page: PageId }) {
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
