import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "AI Quản lý đồng hồ điện",
  description: "Hệ thống nội bộ xử lý hình ảnh đồng hồ điện bằng AI",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
