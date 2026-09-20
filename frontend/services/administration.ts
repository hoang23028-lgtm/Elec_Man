import { apiJson } from "@/services/http";

export type Setting = {
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

export async function startTraining(csrfToken: string): Promise<TrainingRun> {
  return apiJson<TrainingRun>(
    "/training/runs",
    { method: "POST", headers: { "X-CSRF-Token": csrfToken } },
    "Không thể tạo phiên huấn luyện.",
  );
}
