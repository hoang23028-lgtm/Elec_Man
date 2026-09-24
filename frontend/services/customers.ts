import { apiFetch, apiJson } from "@/services/http";

export type CustomerSummary = {
  total: number;
  matched_readings: number;
  unmatched_readings: number;
};

export type CustomerImportResult = {
  total: number;
  created: number;
  updated: number;
  reconciled_readings: number;
};

export async function getCustomerSummary(): Promise<CustomerSummary> {
  return apiJson<CustomerSummary>(
    "/customers/summary",
    {},
    "Không thể tải thông tin dữ liệu khách hàng.",
  );
}

export async function importCustomerFile(
  file: File,
  csrfToken: string,
): Promise<CustomerImportResult> {
  const data = new FormData();
  data.append("file", file);
  const response = await apiFetch(
    "/customers/import",
    {
      method: "POST",
      headers: { "X-CSRF-Token": csrfToken },
      body: data,
    },
    "Không thể nhập dữ liệu khách hàng.",
  );
  return response.json() as Promise<CustomerImportResult>;
}
