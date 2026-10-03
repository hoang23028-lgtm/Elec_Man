import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Quản lý đồng hồ điện",
  description: "Hệ thống xử lý hình ảnh đồng hồ điện",
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
