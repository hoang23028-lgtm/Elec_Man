"use client";
import { useEffect, useState } from "react";
import { getDashboard, type Dashboard } from "@/services/system";
export function DashboardSummary({ csrfToken }: { csrfToken?: string }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function load() {
    try {
      setData(await getDashboard());
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể tải bảng điều khiển.",
      );
    }
  }
  useEffect(() => {
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 10000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Bảng điều khiển</p>
          <h2>Tổng quan hệ thống</h2>
        </div>
        <button className="secondary" type="button" onClick={() => void load()}>
          Làm mới
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="metrics">
        <div>
          <strong>{data?.batches ?? "—"}</strong>
          <span>Lô dữ liệu</span>
        </div>
        <div>
          <strong>{data?.images ?? "—"}</strong>
          <span>Hình ảnh</span>
        </div>
        <div>
          <strong>{data?.jobs.COMPLETED ?? "—"}</strong>
          <span>Tác vụ hoàn tất</span>
        </div>
        <div>
          <strong>{data?.jobs.FAILED ?? "—"}</strong>
          <span>Tác vụ thất bại</span>
        </div>
      </div>
      {!csrfToken && (
        <p className="read-only-note">
          Chế độ công khai · Đăng nhập quản trị để truy cập hồ sơ vận hành.
        </p>
      )}
    </section>
  );
}
