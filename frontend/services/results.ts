import { apiFetch, paginatedJson } from "@/services/http";
export type Result = {
  image_id: string;
  original_filename: string;
  image_status: string;
  ai_status: string;
  customer_id_ai: string | null;
  meter_reading_ai: string | null;
  final_confidence: number;
  review_status: string | null;
  auto_confirmed: boolean;
  final_customer_id: string | null;
  final_meter_reading: string | null;
};
export type ResultQuery = {
  offset?: number;
  limit?: number;
  imageStatus?: string;
  search?: string;
};
export async function getResultsPage(
  query: ResultQuery = {},
): Promise<{ items: Result[]; total: number }> {
  const params = new URLSearchParams();
  if (query.offset) params.set("offset", String(query.offset));
  if (query.limit) params.set("limit", String(query.limit));
  if (query.imageStatus) params.set("image_status", query.imageStatus);
  if (query.search) params.set("search", query.search);
  const suffix = params.size ? `?${params.toString()}` : "";
  return paginatedJson<Result>(`/results${suffix}`, "Không thể tải kết quả.");
}
export async function reviewResult(
  id: string,
  csrf: string,
  action: "CONFIRM" | "REJECT",
  customer: string,
  reading: string,
): Promise<void> {
  await apiFetch(`/results/${id}/review`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({
      action,
      final_customer_id: customer || null,
      final_meter_reading: reading || null,
    }),
  }, "Kiểm duyệt thất bại.");
}
