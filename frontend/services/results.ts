import { apiFetch, paginatedJson } from "@/services/http";
export type ReadingBoundingBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};
export type ReadingPoint = { x: number; y: number };
export type ReadingPolygon = { points: ReadingPoint[] };
export type Result = {
  image_id: string;
  original_filename: string;
  image_width: number;
  image_height: number;
  image_status: string;
  ai_status: string;
  customer_id_ai: string | null;
  meter_reading_ai: string | null;
  final_confidence: number;
  review_status: string | null;
  auto_confirmed: boolean;
  final_customer_id: string | null;
  final_meter_reading: string | null;
  customer_match_status: string;
  matched_customer_name: string | null;
  matched_meter_serial: string | null;
  reading_bbox: ReadingBoundingBox | null;
  reading_polygon: ReadingPolygon | null;
  ai_reading_bbox: ReadingBoundingBox | null;
};
export type RecognitionStatus = {
  image_id: string;
  job_id: string;
  status: string;
  meter_reading_ai: string | null;
  meter_confidence: number | null;
  error_message: string | null;
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
  readingPolygon: ReadingPolygon | null,
): Promise<void> {
  await apiFetch(`/results/${id}/review`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({
      action,
      final_customer_id: customer || null,
      final_meter_reading: reading || null,
      reading_polygon: readingPolygon,
    }),
  }, "Kiểm duyệt thất bại.");
}

export async function recognizeReading(
  id: string,
  csrf: string,
  readingPolygon: ReadingPolygon,
): Promise<void> {
  await apiFetch(`/results/${id}/recognize-reading`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ reading_polygon: readingPolygon }),
  }, "Không thể đưa vùng chỉ số vào hàng đợi nhận diện.");
}

export async function getRecognitionStatus(id: string): Promise<RecognitionStatus> {
  const response = await apiFetch(
    `/results/${id}/recognize-reading`,
    undefined,
    "Không thể kiểm tra trạng thái nhận diện.",
  );
  return response.json() as Promise<RecognitionStatus>;
}
