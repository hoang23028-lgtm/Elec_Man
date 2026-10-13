"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { Pagination } from "@/components/pagination";
import { usePolling } from "@/hooks/use-polling";
import { useLatestRequest } from "@/hooks/use-latest-request";
import {
  getBillingDashboard,
  getDashboard,
  type BillingDashboard,
  type Dashboard,
} from "@/services/system";

const pageSize = 12;
const months = Array.from({ length: 12 }, (_, index) => index + 1);
const numberFormatter = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 });
const moneyFormatter = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});
const dateFormatter = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

type AppliedFilters = { customerId: string; month: string; year: string };

function pageCount(total: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

export function DashboardSummary({ readOnly = true }: { readOnly?: boolean }) {
  const request = useLatestRequest();
  const [operations, setOperations] = useState<Dashboard | null>(null);
  const [billing, setBilling] = useState<BillingDashboard | null>(null);
  const [customerInput, setCustomerInput] = useState("");
  const [monthInput, setMonthInput] = useState("");
  const [yearInput, setYearInput] = useState("");
  const [filters, setFilters] = useState<AppliedFilters>({
    customerId: "",
    month: "",
    year: "",
  });
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const load = useCallback(
    async (showLoading = false) => {
      const revision = request.begin();
      if (showLoading) setLoading(true);
      try {
        const [nextOperations, nextBilling] = await Promise.all([
          getDashboard(),
          getBillingDashboard({
            customerId: filters.customerId || undefined,
            month: filters.month ? Number(filters.month) : undefined,
            year: filters.year ? Number(filters.year) : undefined,
            offset: page * pageSize,
            limit: pageSize,
          }),
        ]);
        if (!request.isCurrent(revision)) return;
        const lastPage = Math.max(0, Math.ceil(nextBilling.total / pageSize) - 1);
        if (page > lastPage) { setPage(lastPage); return; }
        setOperations(nextOperations);
        setBilling(nextBilling);
        setUpdatedAt(new Date());
        setError(null);
      } catch (reason) {
        if (!request.isCurrent(revision)) return;
        setError(
          reason instanceof Error
            ? reason.message
            : "Không thể tải bảng điều khiển.",
        );
      } finally {
        if (request.isCurrent(revision)) setLoading(false);
      }
    },
    [filters, page, request],
  );

  useEffect(() => {
    void load(true);
  }, [load]);
  usePolling(() => load(false), 30000, autoRefresh);
  useEffect(() => {
    const refresh = () => { void load(false); };
    window.addEventListener("confirmed-data-changed", refresh);
    return () => window.removeEventListener("confirmed-data-changed", refresh);
  }, [load]);

  const trendMaximum = useMemo(
    () => Math.max(0, ...(billing?.trend.map((point) => point.consumption_kwh) ?? [])),
    [billing?.trend],
  );

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    request.invalidate();
    setPage(0);
    setFilters({
      customerId: customerInput.trim(),
      month: monthInput,
      year: yearInput,
    });
  }

  function resetFilters() {
    request.invalidate();
    setCustomerInput("");
    setMonthInput("");
    setYearInput("");
    setPage(0);
    setFilters({ customerId: "", month: "", year: "" });
  }

  const pages = pageCount(billing?.total ?? 0);

  return (
    <section className="panel dashboard-panel" aria-labelledby="dashboard-summary-title">
      <div className="section-heading dashboard-heading">
        <div>
          <p className="eyebrow">Dữ liệu đã xác nhận</p>
          <h2 id="dashboard-summary-title">Tổng quan điện năng và tiền điện</h2>
          <p className="muted">
            Dữ liệu chỉ lấy từ các chỉ số đã xác nhận. Tiền điện được tính theo
            mục đích sử dụng, mức tiêu thụ giữa hai kỳ, biểu giá và VAT theo tháng ghi điện.
          </p>
        </div>
        <button
          className="secondary"
          type="button"
          onClick={() => void load(true)}
          disabled={loading}
        >
          {loading ? "Đang tải…" : "Làm mới"}
        </button>
      </div>

      <div className="dashboard-update-bar">
        <span>{updatedAt ? `Cập nhật ${dateFormatter.format(updatedAt)}` : "Chưa tải xong dữ liệu"}{error && updatedAt ? " · Dữ liệu cũ, chưa làm mới được" : ""}</span>
        <button type="button" className="secondary" aria-pressed={autoRefresh} onClick={() => setAutoRefresh((value) => !value)}>{autoRefresh ? "Tự cập nhật: bật (30 giây)" : "Tự cập nhật: tắt"}</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}

      <div className="metrics dashboard-operations-metrics" aria-label="Thống kê vận hành">
        <div><strong>{operations?.batches ?? "—"}</strong><span>Lô dữ liệu</span></div>
        <div><strong>{operations?.images ?? "—"}</strong><span>Hình ảnh</span></div>
        <div><strong>{operations?.jobs.COMPLETED ?? "—"}</strong><span>Tác vụ hoàn tất</span></div>
        <div><strong>{operations?.jobs.FAILED ?? "—"}</strong><span>Tác vụ thất bại</span></div>
      </div>

      <div className="dashboard-divider" />

      <div className="dashboard-section-heading">
        <div>
          <p className="eyebrow">Thống kê theo bộ lọc</p>
          <h3>Điện năng đã xác nhận</h3>
        </div>
        <span className="badge">
          Số tiền tham khảo · {billing?.vat_rate_percent != null
            ? `VAT ${billing.vat_rate_percent}%`
            : "VAT theo từng kỳ"}
        </span>
      </div>
      <div className="metrics billing-metrics" aria-label="Thống kê điện năng">
        <div><strong>{billing?.summary.total_customers ?? "—"}</strong><span>Khách hàng</span></div>
        <div><strong>{billing ? numberFormatter.format(billing.summary.total_consumption_kwh) : "—"}</strong><span>Điện tiêu thụ (kWh)</span></div>
        <div><strong>{billing ? moneyFormatter.format(billing.summary.energy_charge_before_vat_vnd) : "—"}</strong><span>Tiền điện trước VAT</span></div>
        <div><strong>{billing ? moneyFormatter.format(billing.summary.estimated_amount_vnd) : "—"}</strong><span>Tổng tạm tính sau VAT</span></div>
        <div><strong>{billing?.summary.billed_records ?? "—"}/{billing?.summary.total_records ?? "—"}</strong><span>Kỳ đủ dữ liệu tính</span></div>
      </div>

      <form className="dashboard-filters" onSubmit={applyFilters} role="search">
        <label>
          Mã khách hàng
          <input
            value={customerInput}
            onChange={(event) => setCustomerInput(event.target.value)}
            placeholder="Ví dụ: PN2.001"
          />
        </label>
        <label>
          Tháng
          <select value={monthInput} onChange={(event) => setMonthInput(event.target.value)}>
            <option value="">Tất cả tháng</option>
            {months.map((month) => <option value={month} key={month}>Tháng {month}</option>)}
          </select>
        </label>
        <label>
          Năm
          <select value={yearInput} onChange={(event) => setYearInput(event.target.value)}>
            <option value="">Tất cả năm</option>
            {billing?.available_years.map((year) => <option value={year} key={year}>{year}</option>)}
          </select>
        </label>
        <div className="dashboard-filter-actions">
          <button type="submit" disabled={loading}>Lọc dữ liệu</button>
          <button className="secondary" type="button" onClick={resetFilters} disabled={loading}>Xóa lọc</button>
        </div>
      </form>

      {billing?.trend.length ? (
        <section className="billing-trend" aria-labelledby="billing-trend-title">
          <div className="dashboard-section-heading compact">
            <div>
              <p className="eyebrow">Xu hướng</p>
              <h3 id="billing-trend-title">Mức tiêu thụ theo tháng</h3>
            </div>
            <span className="muted">Đơn vị: kWh</span>
          </div>
          <div className="trend-list">
            {billing.trend.map((point) => (
              <div className="trend-row" key={`${point.year}-${point.month}`}>
                <span>Tháng {point.month}/{point.year}</span>
                <div className="trend-track" aria-hidden="true">
                  <span
                    style={{
                      width: `${trendMaximum ? Math.max(3, point.consumption_kwh / trendMaximum * 100) : 3}%`,
                    }}
                  />
                </div>
                <strong>{numberFormatter.format(point.consumption_kwh)}</strong>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <div className="dashboard-section-heading billing-table-heading">
        <div>
          <p className="eyebrow">Danh sách tiền điện</p>
          <h3>Khách hàng và chỉ số theo kỳ</h3>
        </div>
        <span className="muted">{billing?.total ?? 0} bản ghi</span>
      </div>
      <p className="table-scroll-hint">Cuộn ngang bảng để xem đầy đủ các cột.</p>
      <div className="table-wrap dashboard-billing-table" aria-busy={loading} role="region" aria-label="Danh sách tiền điện, có thể cuộn ngang" tabIndex={0}>
        <table>
          <thead>
            <tr>
              <th className="row-number">STT</th>
              <th>Kỳ ghi nhận</th>
              <th>Mã khách hàng</th>
              <th>Chỉ số trước</th>
              <th>Chỉ số hiện tại</th>
              <th>Tiêu thụ</th>
              <th>Biểu giá áp dụng</th>
              <th>Trước VAT</th>
              <th>VAT</th>
              <th>Tổng tạm tính</th>
            </tr>
          </thead>
          <tbody>
            {loading && !billing && <tr><td colSpan={10} role="status">Đang tải dữ liệu tiền điện…</td></tr>}
            {billing?.records.map((record, index) => (
              <tr key={record.reading_id}>
                <td className="row-number">{page * pageSize + index + 1}</td>
                <td title={`Xác nhận: ${dateFormatter.format(new Date(record.reading_at))}`}>{String(record.month).padStart(2, "0")}/{record.year}</td>
                <td><strong>{record.customer_id}</strong></td>
                <td>{record.previous_reading ?? "—"}</td>
                <td>{record.current_reading}</td>
                <td>
                  {record.consumption_kwh === null ? (
                    <span className="muted">Chưa đủ kỳ trước</span>
                  ) : (
                    `${numberFormatter.format(record.consumption_kwh)} kWh`
                  )}
                </td>
                <td>
                  {record.tariff_label ?? "Chưa xác định"}
                  {record.tariff_version && record.tariff_source_url && (
                    <small><a href={record.tariff_source_url} target="_blank" rel="noopener noreferrer">{record.tariff_version}</a></small>
                  )}
                  {record.tariff_estimated && <small>Tạm tính theo dưới 6 kV, giờ bình thường</small>}
                  {record.billing_note && <small>{record.billing_note}</small>}
                </td>
                <td>
                  {record.energy_charge_before_vat_vnd === null
                    ? "—"
                    : moneyFormatter.format(record.energy_charge_before_vat_vnd)}
                </td>
                <td>
                  {record.vat_amount_vnd === null
                    ? "—"
                    : moneyFormatter.format(record.vat_amount_vnd)}
                  {record.vat_rate_percent != null && record.vat_source_url && (
                    <small><a href={record.vat_source_url} target="_blank" rel="noopener noreferrer" title={record.vat_policy ?? undefined}>VAT {record.vat_rate_percent}% · {record.vat_policy}</a></small>
                  )}
                </td>
                <td>
                  {record.estimated_amount_vnd === null
                    ? "—"
                    : moneyFormatter.format(record.estimated_amount_vnd)}
                </td>
              </tr>
            ))}
            {!loading && !billing?.records.length && (
              <tr>
                <td colSpan={10} className="empty-state">
                  <strong>Chưa có chỉ số đã xác nhận trong phạm vi này</strong>
                  <p>Thử đổi tháng, năm hoặc xóa bộ lọc. Ảnh mới tải và nhãn chưa xác nhận chưa được tính vào bảng điện năng.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Pagination
        pageIndex={page}
        totalPages={pages}
        onPageChange={setPage}
        ariaLabel="Phân trang danh sách tiền điện"
        disabled={loading}
        itemSummary={`${billing?.total ?? 0} bản ghi`}
      />

      <p className="billing-disclaimer">
        Sinh hoạt áp dụng lũy tiến 6 bậc. Sản xuất, kinh doanh và hành chính sự nghiệp
        đang tạm tính theo cấp điện áp dưới 6 kV, giờ bình thường vì dữ liệu hiện tại
        chưa tách ba khung giờ. Chưa bao gồm công suất phản kháng, truy thu hoặc điều chỉnh khác.
        Tháng thay đổi giá giữa kỳ chưa được tính khi thiếu dữ liệu phân bổ. Tổng tiền chỉ cộng các kỳ đủ dữ liệu, không phải hóa đơn chính thức.
      </p>
      {readOnly && (
        <p className="read-only-note">
          Chế độ chỉ xem · Bạn có thể tra cứu và lọc dữ liệu. Các thao tác nghiệp vụ yêu cầu tài khoản quản trị vận hành hoặc quản trị toàn hệ thống.
        </p>
      )}
    </section>
  );
}
