const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

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

async function checked(response: Response): Promise<Response> {
  if (response.ok) return response;
  const body: { detail?: string } = await response.json().catch(() => ({}));
  throw new Error(body.detail ?? "Yêu cầu quản trị thất bại.");
}

export async function getSettings(): Promise<Setting[]> {
  return checked(
    await fetch(`${api}/settings`, { credentials: "include" }),
  ).then((response) => response.json());
}

export async function saveSettings(
  values: Record<string, number>,
  csrfToken: string,
): Promise<Setting[]> {
  return checked(
    await fetch(`${api}/settings`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({ values }),
    }),
  ).then((response) => response.json());
}

export async function getModels(): Promise<ModelRecord[]> {
  return checked(await fetch(`${api}/models`, { credentials: "include" })).then(
    (response) => response.json(),
  );
}

export async function registerModel(
  input: ModelInput,
  csrfToken: string,
): Promise<ModelRecord> {
  return checked(
    await fetch(`${api}/models`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(input),
    }),
  ).then((response) => response.json());
}

export async function activateModel(
  id: string,
  csrfToken: string,
): Promise<ModelRecord> {
  return checked(
    await fetch(`${api}/models/${id}/activate`, {
      method: "PUT",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken },
    }),
  ).then((response) => response.json());
}

export async function getEvaluation(modelVersion = ""): Promise<Evaluation> {
  const query = modelVersion
    ? `?model_version=${encodeURIComponent(modelVersion)}`
    : "";
  return checked(
    await fetch(`${api}/evaluation/summary${query}`, {
      credentials: "include",
    }),
  ).then((response) => response.json());
}
