import { apiJson } from "@/services/http";
export type Dashboard = {
  batches: number;
  images: number;
  jobs: Record<string, number>;
};
export type BillingSummary = {
  total_customers: number;
  total_records: number;
  billed_records: number;
  total_consumption_kwh: number;
  average_consumption_kwh: number | null;
  estimated_amount_vnd: number;
};
export type BillingRecord = {
  reading_id: string;
  customer_id: string;
  reading_at: string;
  month: number;
  year: number;
  previous_reading: string | null;
  current_reading: string;
  consumption_kwh: number | null;
  estimated_amount_vnd: number | null;
};
export type BillingTrendPoint = {
  month: number;
  year: number;
  record_count: number;
  consumption_kwh: number;
  estimated_amount_vnd: number;
};
export type BillingDashboard = {
  summary: BillingSummary;
  records: BillingRecord[];
  trend: BillingTrendPoint[];
  available_years: number[];
  unit_price_vnd: number;
  total: number;
  offset: number;
  limit: number;
};
export type BillingFilters = {
  customerId?: string;
  month?: number;
  year?: number;
  offset?: number;
  limit?: number;
};
export async function getDashboard(): Promise<Dashboard> {
  return apiJson<Dashboard>("/dashboard", {}, "Không thể tải bảng điều khiển.");
}
export async function getBillingDashboard(
  filters: BillingFilters = {},
): Promise<BillingDashboard> {
  const query = new URLSearchParams();
  if (filters.customerId) query.set("customer_id", filters.customerId);
  if (filters.month) query.set("month", String(filters.month));
  if (filters.year) query.set("year", String(filters.year));
  query.set("offset", String(filters.offset ?? 0));
  query.set("limit", String(filters.limit ?? 12));
  return apiJson<BillingDashboard>(
    `/dashboard/billing?${query.toString()}`,
    {},
    "Không thể tải dữ liệu điện năng.",
  );
}
export async function exportConfirmed(csrfToken: string): Promise<string> {
  const body = await apiJson<{ download_url: string }>("/exports/final", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  }, "Không thể tạo tệp Excel.");
  return body.download_url;
}
