import { apiFetch, apiJson, paginatedJson } from "@/services/http";
export type ReadingBoundingBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};
export type ReadingPoint = { x: number; y: number };
export type ReadingPolygon = { points: ReadingPoint[] };
export type Result = {
  reading_month: string | null;
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
  meter_polygon: ReadingPolygon | null;
  ai_meter_bbox: ReadingBoundingBox | null;
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
  reviewStatus?: string;
  offset?: number;
  limit?: number;
  imageStatus?: string;
  search?: string;
};
export type ResultStatusCounts = {
  review_required: number;
  pending: number;
  labeled: number;
  confirmed: number;
  rejected: number;
};
export async function getResultStatusCounts(search?: string): Promise<ResultStatusCounts> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiJson<ResultStatusCounts>(
    `/results/status-counts${suffix}`,
    {},
    "Không thể tải số lượng trạng thái.",
  );
}
export async function getResultsPage(
  query: ResultQuery = {},
): Promise<{ items: Result[]; total: number }> {
  const params = new URLSearchParams();
  if (query.offset) params.set("offset", String(query.offset));
  if (query.limit) params.set("limit", String(query.limit));
  if (query.imageStatus) params.set("image_status", query.imageStatus);
  if (query.search) params.set("search", query.search);
  if (query.reviewStatus) params.set("review_status", query.reviewStatus);
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
  readingMonth: string,
  meterPolygon?: ReadingPolygon | null,
): Promise<void> {
  await apiFetch(`/results/${id}/review`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({
      action,
      final_customer_id: customer || null,
      final_meter_reading: reading || null,
      reading_polygon: readingPolygon,
      reading_month: readingMonth ? `${readingMonth}-01` : null,
      meter_polygon: meterPolygon,
    }),
  }, "Kiểm duyệt thất bại.");
}

export async function recognizeReading(
  id: string,
  csrf: string,
  readingPolygon: ReadingPolygon,
  integerDigits: number,
): Promise<void> {
  await apiFetch(`/results/${id}/recognize-reading`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ reading_polygon: readingPolygon, integer_digits: integerDigits }),
  }, "Không thể đưa vùng chỉ số vào hàng đợi nhận diện.");
}

export async function saveTrainingLabel(
  id: string,
  csrf: string,
  reading: string,
  readingPolygon: ReadingPolygon,
  meterPolygon: ReadingPolygon | null,
): Promise<void> {
  await apiFetch(`/results/${id}/training-label`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({
      final_meter_reading: reading,
      reading_polygon: readingPolygon,
      meter_polygon: meterPolygon,
    }),
  }, "Không thể lưu nhãn huấn luyện.");
}

export async function saveMeterRegion(id: string, csrf: string, polygon: ReadingPolygon): Promise<ReadingPolygon> {
  const response = await apiFetch(`/results/${id}/meter-region`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ meter_polygon: polygon }),
  }, "Không lưu được vùng công tơ. Vùng bạn vẽ vẫn được giữ để thử lại.");
  const result = await response.json() as { meter_polygon: ReadingPolygon };
  return result.meter_polygon;
}

export async function getRecognitionStatus(id: string): Promise<RecognitionStatus> {
  const response = await apiFetch(
    `/results/${id}/recognize-reading`,
    undefined,
    "Không thể kiểm tra trạng thái nhận diện.",
  );
  return response.json() as Promise<RecognitionStatus>;
}
