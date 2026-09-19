import type { Batch, BatchImage } from "@/types/batch";
import { apiFetch, apiJson, paginatedJson, type PageData } from "@/services/http";

export async function createBatch(
  folderName: string,
  csrfToken: string,
): Promise<Batch> {
  return apiJson<Batch>("/batches", {
    method: "POST",
    body: JSON.stringify({ original_folder_name: folderName }),
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
  });
}

export async function uploadImage(
  batchId: string,
  file: File,
  csrfToken: string,
): Promise<void> {
  const data = new FormData();
  data.append("file", file, file.name);
  await apiFetch(`/batches/${batchId}/images`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: data,
  });
}

export async function startBatch(
  batchId: string,
  csrfToken: string,
): Promise<Batch> {
  return apiJson<Batch>(`/batches/${batchId}/start`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export async function getBatchesPage(
  offset = 0,
  limit = 8,
): Promise<PageData<Batch>> {
  return paginatedJson<Batch>(
    `/batches?offset=${offset}&limit=${limit}`,
    "Không thể tải danh sách lô.",
  );
}

export async function getBatchImages(
  batchId: string,
  offset = 0,
  limit = 12,
): Promise<PageData<BatchImage>> {
  return paginatedJson<BatchImage>(
    `/batches/${batchId}/images?offset=${offset}&limit=${limit}`,
    "Không thể tải chi tiết lô dữ liệu.",
  );
}
