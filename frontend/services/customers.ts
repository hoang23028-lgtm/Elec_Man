import { apiFetch, apiJson, paginatedJson } from "@/services/http";

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

export type CustomerRecord = {
  id: string;
  customer_code: string;
  full_name: string;
  address: string;
  electricity_route: string;
  meter_serial: string;
  initial_reading: number;
  usage_purpose: string;
  created_at: string;
  updated_at: string;
};

export type CustomerCreateInput = {
  customer_code: string;
  full_name: string;
  address: string;
  electricity_route: string;
  meter_serial: string;
  initial_reading: number;
  usage_purpose: string;
};

export async function getCustomerSummary(): Promise<CustomerSummary> {
  return apiJson<CustomerSummary>(
    "/customers/summary",
    {},
    "Không thể tải thông tin dữ liệu khách hàng.",
  );
}

export async function getCustomerUsagePurposes(): Promise<string[]> {
  return apiJson<string[]>(
    "/customers/usage-purposes",
    {},
    "Không thể tải danh sách mục đích sử dụng.",
  );
}

export async function getCustomers(offset: number, limit: number, search: string) {
  const query = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (search) query.set("search", search);
  return paginatedJson<CustomerRecord>(
    `/customers?${query}`,
    "Không thể tải danh sách khách hàng.",
  );
}

export async function createCustomer(
  input: CustomerCreateInput,
  csrfToken: string,
): Promise<CustomerRecord> {
  return apiJson<CustomerRecord>(
    "/customers",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(input),
    },
    "Không thể thêm khách hàng.",
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
