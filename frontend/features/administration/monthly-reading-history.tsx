"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { Pagination } from "@/components/pagination";
import { getBillingDashboard, type BillingDashboard } from "@/services/system";

const PAGE_SIZE = 15;
const months = Array.from({ length: 12 }, (_, index) => index + 1);
const numberFormatter = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 });

type ReadingFilters = {
  customerId: string;
  month: string;
  year: string;
};

const emptyFilters = (): ReadingFilters => ({ customerId: "", month: "", year: "" });

export function MonthlyReadingHistory() {
  const [inputs, setInputs] = useState<ReadingFilters>(emptyFilters);
  const [filters, setFilters] = useState<ReadingFilters>(emptyFilters);
  const [result, setResult] = useState<BillingDashboard | null>(null);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setResult(
        await getBillingDashboard({
          customerId: filters.customerId || undefined,
          month: filters.month ? Number(filters.month) : undefined,
          year: filters.year ? Number(filters.year) : undefined,
          offset: page * PAGE_SIZE,
          limit: PAGE_SIZE,
        }),
      );
      setError(null);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể tải lịch sử chỉ số điện.",
      );
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(0);
    setFilters({ ...inputs, customerId: inputs.customerId.trim() });
  }

  function resetFilters() {
    const cleared = emptyFilters();
    setInputs(cleared);
    setFilters(cleared);
    setPage(0);
  }

  const totalPages = Math.max(1, Math.ceil((result?.total ?? 0) / PAGE_SIZE));

  return (
    <section
      className="panel full-span monthly-history-panel"
      aria-labelledby="monthly-history-title"
      aria-busy={loading}
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Lịch sử chỉ số</p>
          <h2 id="monthly-history-title">Chỉ số điện theo tháng</h2>
          <p className="muted">
            Tra cứu các chỉ số đã được xác nhận và lưu vào cơ sở dữ liệu theo mã
            khách hàng, tháng và năm.
          </p>
        </div>
        <button className="secondary" type="button" onClick={() => void load()} disabled={loading}>
          {loading ? "Đang tải…" : "Làm mới"}
        </button>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <form className="dashboard-filters" onSubmit={applyFilters} role="search">
        <label htmlFor="monthly-history-customer">
          Mã khách hàng
          <input
            id="monthly-history-customer"
            value={inputs.customerId}
            onChange={(event) =>
              setInputs((current) => ({ ...current, customerId: event.target.value }))
            }
            placeholder="Ví dụ: PN2.001"
            maxLength={128}
          />
        </label>
        <label htmlFor="monthly-history-month">
          Tháng
          <select
            id="monthly-history-month"
            value={inputs.month}
            onChange={(event) =>
              setInputs((current) => ({ ...current, month: event.target.value }))
            }
          >
            <option value="">Tất cả tháng</option>
            {months.map((month) => (
              <option value={month} key={month}>Tháng {month}</option>
            ))}
          </select>
        </label>
        <label htmlFor="monthly-history-year">
          Năm
          <select
            id="monthly-history-year"
            value={inputs.year}
            onChange={(event) =>
              setInputs((current) => ({ ...current, year: event.target.value }))
            }
          >
            <option value="">Tất cả năm</option>
            {result?.available_years.map((year) => (
              <option value={year} key={year}>{year}</option>
            ))}
          </select>
        </label>
        <div className="dashboard-filter-actions">
          <button type="submit" disabled={loading}>Lọc dữ liệu</button>
          <button className="secondary" type="button" onClick={resetFilters} disabled={loading}>
            Xóa lọc
          </button>
        </div>
      </form>

      <div className="metrics monthly-history-metrics" aria-label="Thống kê lịch sử chỉ số">
        <div>
          <strong>{result?.summary.total_customers ?? "—"}</strong>
          <span>Khách hàng</span>
        </div>
        <div>
          <strong>{result?.summary.total_records ?? "—"}</strong>
          <span>Bản ghi đã xác nhận</span>
        </div>
        <div>
          <strong>
            {result
              ? numberFormatter.format(result.summary.total_consumption_kwh)
              : "—"}
          </strong>
          <span>Điện tiêu thụ (kWh)</span>
        </div>
      </div>

      <div className="dashboard-section-heading billing-table-heading">
        <div>
          <p className="eyebrow">Kết quả tra cứu</p>
          <h3>Lịch sử chỉ số đã xác nhận</h3>
        </div>
        <span className="muted">{result?.total ?? 0} bản ghi</span>
      </div>
      <div className="table-wrap dashboard-billing-table" aria-busy={loading}>
        <table>
          <thead>
            <tr>
              <th className="row-number">STT</th>
              <th>Kỳ chỉ số</th>
              <th>Mã khách hàng</th>
              <th>Chỉ số trước</th>
              <th>Chỉ số hiện tại</th>
              <th>Điện tiêu thụ</th>
            </tr>
          </thead>
          <tbody>
            {result?.records.map((record, index) => (
              <tr key={record.reading_id}>
                <td className="row-number">{page * PAGE_SIZE + index + 1}</td>
                <td>Tháng {record.month}/{record.year}</td>
                <td><strong>{record.customer_id}</strong></td>
                <td>{record.previous_reading ?? "—"}</td>
                <td>{record.current_reading}</td>
                <td>
                  {record.consumption_kwh === null
                    ? "Chưa đủ dữ liệu"
                    : `${numberFormatter.format(record.consumption_kwh)} kWh`}
                </td>
              </tr>
            ))}
            {!loading && !result?.records.length && (
              <tr>
                <td colSpan={6} className="empty-state">
                  Không có chỉ số đã xác nhận phù hợp với bộ lọc.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Pagination
        pageIndex={page}
        totalPages={totalPages}
        onPageChange={setPage}
        ariaLabel="Phân trang lịch sử chỉ số điện"
        disabled={loading}
        itemSummary={`${result?.total ?? 0} bản ghi`}
      />
    </section>
  );
}
