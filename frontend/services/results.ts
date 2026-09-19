const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";
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
export async function getResults(query: ResultQuery = {}): Promise<Result[]> {
  return (await getResultsPage(query)).items;
}
export async function getResultsPage(
  query: ResultQuery = {},
): Promise<{ items: Result[]; total: number }> {
  const params = new URLSearchParams();
  if (query.offset) params.set("offset", String(query.offset));
  if (query.limit) params.set("limit", String(query.limit));
  if (query.imageStatus) params.set("image_status", query.imageStatus);
  if (query.search) params.set("search", query.search);
  const suffix = params.size ? `?${params.toString()}` : "";
  const r = await fetch(`${api}/results${suffix}`, { credentials: "include" });
  if (!r.ok) throw new Error("Không thể tải kết quả.");
  return {
    items: (await r.json()) as Result[],
    total: Number(r.headers.get("X-Total-Count") ?? 0),
  };
}
export async function reviewResult(
  id: string,
  csrf: string,
  action: "CONFIRM" | "REJECT",
  customer: string,
  reading: string,
): Promise<void> {
  const r = await fetch(`${api}/results/${id}/review`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({
      action,
      final_customer_id: customer || null,
      final_meter_reading: reading || null,
    }),
  });
  if (!r.ok) {
    const b: { detail?: string } = await r.json().catch(() => ({}));
    throw new Error(b.detail ?? "Kiểm duyệt thất bại.");
  }
}
