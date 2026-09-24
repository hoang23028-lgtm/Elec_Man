"use client";

import { useState } from "react";

import { exportConfirmed, type ExportBundle } from "@/services/system";

const today = new Date();
const currentPeriod = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

export function MonthlyExport({ csrfToken }: { csrfToken: string }) {
  const [period, setPeriod] = useState(currentPeriod);
  const [exporting, setExporting] = useState(false);
  const [bundle, setBundle] = useState<ExportBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function createReport() {
    const [year, month] = period.split("-").map(Number);
    if (!year || !month) {
      setError("Hãy chọn tháng cần xuất báo cáo.");
      return;
    }
    setExporting(true);
    setBundle(null);
    setError(null);
    setMessage(null);
    try {
      const result = await exportConfirmed(csrfToken, month, year);
      setBundle(result);
      setMessage(
        `Đã tạo báo cáo tháng ${month}/${year} gồm ${result.exported_rows} khách hàng.`,
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tạo báo cáo theo tháng.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <section
      className="panel full-span monthly-export-panel"
      aria-labelledby="monthly-export-title"
      aria-busy={exporting}
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Báo cáo chỉ số</p>
          <h2 id="monthly-export-title">Xuất dữ liệu theo tháng</h2>
          <p className="muted">
            Mỗi khách hàng chỉ lấy chỉ số đã xác nhận mới nhất trong tháng. File Excel và
            JSON có cùng 7 trường như tệp khách hàng mẫu; chỉ số kỳ này được ghi vào
            trường chi_so_khoi_tao để dùng cho kỳ tiếp theo.
          </p>
        </div>
      </div>

      <div className="monthly-export-form">
        <label htmlFor="monthly-export-period">
          Tháng báo cáo
          <input
            id="monthly-export-period"
            type="month"
            value={period}
            onChange={(event) => {
              setPeriod(event.target.value);
              setBundle(null);
              setMessage(null);
              setError(null);
            }}
            min="2000-01"
            max="2100-12"
            required
          />
        </label>
        <button
          type="button"
          onClick={() => void createReport()}
          disabled={exporting || !period}
        >
          {exporting ? "Đang tạo báo cáo…" : "Tạo báo cáo theo tháng"}
        </button>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="notice" role="status">{message}</p>}
      {bundle && (
        <div className="export-downloads monthly-export-downloads">
          <a className="button-link" href={bundle.excel_download_url}>Tải Excel</a>
          <a className="button-link secondary" href={bundle.json_download_url}>Tải JSON</a>
        </div>
      )}
    </section>
  );
}
