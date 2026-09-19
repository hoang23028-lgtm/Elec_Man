import type { Batch, BatchImage } from "@/types/batch";

export type PageData<T> = { items: T[]; total: number };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

async function request(
  path: string,
  csrfToken: string,
  init: RequestInit,
): Promise<Response> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: { ...init.headers, "X-CSRF-Token": csrfToken },
  });
  if (!response.ok) {
    const body: { detail?: string } = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Yêu cầu thất bại.");
  }
  return response;
}

export async function createBatch(
  folderName: string,
  csrfToken: string,
): Promise<Batch> {
  const response = await request("/batches", csrfToken, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original_folder_name: folderName }),
  });
  return response.json() as Promise<Batch>;
}

export async function uploadImage(
  batchId: string,
  file: File,
  csrfToken: string,
): Promise<void> {
  const data = new FormData();
  data.append("file", file, file.name);
  await request(`/batches/${batchId}/images`, csrfToken, {
    method: "POST",
    body: data,
  });
}

export async function startBatch(
  batchId: string,
  csrfToken: string,
): Promise<Batch> {
  const response = await request(`/batches/${batchId}/start`, csrfToken, {
    method: "POST",
  });
  return response.json() as Promise<Batch>;
}

export async function getBatches(offset = 0, limit = 8): Promise<Batch[]> {
  return (await getBatchesPage(offset, limit)).items;
}

export async function getBatchesPage(
  offset = 0,
  limit = 8,
): Promise<PageData<Batch>> {
  const response = await fetch(
    `${apiBaseUrl}/batches?offset=${offset}&limit=${limit}`,
    { credentials: "include" },
  );
  if (!response.ok) throw new Error("Không thể tải danh sách lô.");
  return {
    items: (await response.json()) as Batch[],
    total: Number(response.headers.get("X-Total-Count") ?? 0),
  };
}

export async function getBatchImages(
  batchId: string,
  offset = 0,
  limit = 12,
): Promise<PageData<BatchImage>> {
  const response = await fetch(
    `${apiBaseUrl}/batches/${batchId}/images?offset=${offset}&limit=${limit}`,
    { credentials: "include" },
  );
  if (!response.ok) throw new Error("Không thể tải chi tiết lô dữ liệu.");
  return {
    items: (await response.json()) as BatchImage[],
    total: Number(response.headers.get("X-Total-Count") ?? 0),
  };
}
