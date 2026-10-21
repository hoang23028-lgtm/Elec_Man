import { apiJson } from "@/services/http";

export type Setting = {
  editable: boolean;
  source: "database" | "deployment";
  key: string;
  value: string | number | boolean | null;
  description: string;
  updated_at: string;
};
export type ModelRecord = {
  id: string;
  model_name: string;
  model_type: string;
  version: string;
  file_path: string;
  metrics: Record<string, unknown>;
  status: string;
  sha256: string;
  created_at: string;
  activated_at: string | null;
};
export type ModelInput = {
  model_name: string;
  model_type: string;
  version: string;
  file_path: string;
  sha256: string;
  metrics: Record<string, unknown>;
};
export type Evaluation = {
  model_version: string | null;
  total_predictions: number;
  confirmed_samples: number;
  customer_exact_accuracy: number | null;
  meter_exact_accuracy: number | null;
  meter_digit_accuracy: number | null;
  review_rate: number;
  auto_pass_rate: number;
  false_auto_pass_rate: number | null;
};
export type DatasetSummary = {
  uploaded_images: number;
  confirmed_images: number;
  eligible_samples: number;
  minimum_samples: number;
  new_samples_since_last_run: number;
  auto_start_enabled: boolean;
  ready: boolean;
  verified_samples: number;
  training_samples: number;
  validation_samples: number;
  holdout_samples: number;
  unverified_identity_samples: number;
  data_issues: string[];
};
export type TrainingRun = {
  id: string;
  status: string;
  trigger: string;
  stage: string;
  progress: number;
  sample_count: number;
  training_count: number;
  validation_count: number;
  dataset_hash: string | null;
  metrics: Record<string, unknown>;
  error_message: string | null;
  model_id: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};
export type TrainingOverview = { dataset: DatasetSummary; runs: TrainingRun[] };

export async function getSettings(): Promise<Setting[]> {
  return apiJson<Setting[]>("/settings", {}, "Không thể tải cấu hình.");
}

export async function saveSettings(
  values: Record<string, number>,
  csrfToken: string,
): Promise<Setting[]> {
  return apiJson<Setting[]>(
    "/settings",
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({ values }),
    },
    "Không thể lưu cấu hình.",
  );
}

export async function getModels(): Promise<ModelRecord[]> {
  return apiJson<ModelRecord[]>("/models", {}, "Không thể tải mô hình.");
}

export async function registerModel(
  input: ModelInput,
  csrfToken: string,
): Promise<ModelRecord> {
  return apiJson<ModelRecord>(
    "/models",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(input),
    },
    "Không thể đăng ký mô hình.",
  );
}

export async function activateModel(
  id: string,
  csrfToken: string,
): Promise<ModelRecord> {
  return apiJson<ModelRecord>(
    `/models/${id}/activate`,
    {
      method: "PUT",
      headers: { "X-CSRF-Token": csrfToken },
    },
    "Không thể kích hoạt mô hình.",
  );
}

export async function getEvaluation(modelVersion = ""): Promise<Evaluation> {
  const query = modelVersion
    ? `?model_version=${encodeURIComponent(modelVersion)}`
    : "";
  return apiJson<Evaluation>(
    `/evaluation/summary${query}`,
    {},
    "Không thể tải đánh giá.",
  );
}

export async function getTrainingOverview(): Promise<TrainingOverview> {
  return apiJson<TrainingOverview>("/training", {}, "Không thể tải trạng thái huấn luyện.");
}

export type TrainingOptions = { experimental: boolean; fine_tune_reader: boolean; epochs: number; batch_size: number; learning_rate: number; benchmark_deep_locator: boolean; deep_locator_epochs: number };
export async function startTraining(csrfToken: string, options?: TrainingOptions): Promise<TrainingRun> {
  return apiJson<TrainingRun>(
    "/training/runs",
    { method: "POST", headers: { "X-CSRF-Token": csrfToken, "Content-Type": "application/json" }, body: JSON.stringify(options ?? {}) },
    "Không thể tạo phiên huấn luyện.",
  );
}

export type DatasetAnnotation = { revision: number; group_key: string | null; partition: string; identity_verified: boolean; label_verified: boolean; notes: string | null; holdout_locked_at: string | null };
export type DatasetItem = { image_id: string; filename: string; label: string | null; label_revision: number; annotation: Partial<DatasetAnnotation>; issues: string[]; review_status: string };
export type DatasetPage = { total: number; items: DatasetItem[]; summary: { total: number; eligible: number; verified: number; unverified_identity: number; stale_labels: number; train: number; validation: number; holdout: number; conflicts: string[] } };
export const getTrainingData = (offset: number, search: string) => apiJson<DatasetPage>(`/training/data?offset=${offset}&limit=12&search=${encodeURIComponent(search)}`, {}, "Không thể tải dữ liệu huấn luyện.");
export const saveTrainingData = (imageId: string, input: Omit<DatasetAnnotation, "revision" | "holdout_locked_at"> & { expected_revision: number; expected_label_revision: number }, csrfToken: string) => apiJson<DatasetAnnotation>(`/training/data/${imageId}`, { method: "PUT", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: JSON.stringify(input) }, "Không thể lưu phân tập/nhãn.");
export const cancelTraining = (id: string, csrfToken: string) => apiJson(`/training/runs/${id}/cancel`, { method: "POST", headers: { "X-CSRF-Token": csrfToken } }, "Không thể hủy phiên huấn luyện.");
export type OperationalHealth = { observed_at: string; queue: Record<string, number>; stuck_jobs: number; failed_last_24h: number; oldest_pending_seconds: number | null; latency: { samples: number; p50_ms: number | null; p95_ms: number | null }; stage_latency?: Record<string, Record<string, { samples: number; p50_ms: number; p95_ms: number }>>; training: { status: string; progress: number; stage: string; heartbeat_at: string | null } | null; disks: Record<string, { free_bytes: number; total_bytes: number; free_percent: number } | null>; backup: { status: string; completed_at: string | null; verified: boolean } | null; alerts: { severity: string; message: string }[]; note: string };
export const getOperationalHealth = () => apiJson<OperationalHealth>("/training/health", {}, "Không thể tải giám sát hệ thống.");
