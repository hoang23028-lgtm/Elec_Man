type Candidate = { model_type: string; version: string; status?: string; metrics: Record<string, unknown> };
const scoreAtLeast = (value: unknown, minimum: number) => typeof value === "number" && Number.isFinite(value) && value >= minimum && value <= 1;
const enough = (value: unknown) => typeof value === "number" && Number.isInteger(value) && value >= 30;
const object = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

// UX guidance only. Server revalidates checksum, provenance and current labels.
export function activationIssue(record: Candidate, models: Candidate[] = []): string | null {
  const metrics = record.metrics;
  if (!["reading_region_ridge", "meter_locator_ridge", "reading_region_mobilenetv3", "meter_locator_mobilenetv3", "parseq_tiny_finetuned"].includes(record.model_type)) return "Loại mô hình không được hỗ trợ.";
  if (metrics.validation_groups_verified !== true || !enough(metrics.validation_images)) return "Cần 30 ảnh validation tách riêng nhóm đã xác minh.";
  if (metrics.independent_holdout !== true || !enough(metrics.holdout_images) || metrics.end_to_end_evaluated !== true) return "Cần 30 ảnh holdout độc lập và kiểm định toàn quy trình hoàn tất.";
  if (typeof metrics.training_run_id !== "string" || typeof metrics.dataset_hash !== "string") return "Thiếu nguồn phiên huấn luyện đã hoàn tất.";
  const e2e = object(metrics.holdout_end_to_end);
  const family = record.model_type.endsWith("mobilenetv3") ? "mobilenetv3" : typeof metrics.locator_family === "string" ? metrics.locator_family : "ridge";
  const compatible = (kind: string) => models.some((m) => m.model_type === kind && m.version === record.version && m.status === "ACTIVE");
  if (record.model_type === "parseq_tiny_finetuned") {
    const reader = object(metrics.holdout_reader);
    if (![reader.exact_accuracy, reader.coverage].every((value) => scoreAtLeast(value, .95))) return "Bộ đọc cần exact-match và coverage ≥95% trên crop holdout.";
    if (![e2e.exact_accuracy, e2e.coverage].every((value) => scoreAtLeast(value, .9))) return "Toàn quy trình cần exact-match và coverage ≥90%.";
    if (!compatible(`meter_locator_${family}`) || !compatible(`reading_region_${family}`)) return "Kích hoạt hai bộ định vị cùng phiên và cùng kiến trúc trước bộ đọc.";
  } else {
    const meter = record.model_type.startsWith("meter_locator_");
    if (!scoreAtLeast(e2e[meter ? "meter_mean_iou" : "reading_mean_iou"], .8)) return "IoU vùng tương ứng trên holdout phải ≥0,8.";
    if (!scoreAtLeast(metrics[meter ? "validation_meter_region_accuracy" : "validation_region_accuracy"], .8)) return "Điểm vùng validation phải ≥0,8.";
    if (family === "mobilenetv3") {
      const comparison = object(metrics.locator_benchmark);
      const baseline = object(comparison.ridge_end_to_end);
      const key = meter ? "meter_mean_iou" : "reading_mean_iou";
      if (comparison.independent_holdout !== true || baseline.evaluation_complete !== true ||
          ![key, "exact_accuracy", "coverage"].every(k => scoreAtLeast(baseline[k], 0) && scoreAtLeast(e2e[k], baseline[k] as number)) ||
          (e2e[key] as number) <= (baseline[key] as number)) return "Học sâu cần tăng IoU, không giảm độ chính xác/độ phủ so với Ridge trên cùng holdout.";
    }
    if (!meter && metrics.coordinate_space === "meter" && !compatible(`meter_locator_${family}`)) return "Kích hoạt định vị công tơ cùng phiên và kiến trúc trước vùng số.";
  }
  return null;
}
