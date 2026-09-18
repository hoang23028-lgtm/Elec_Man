import type { Batch } from "@/types/batch";

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
    throw new Error(body.detail ?? "Request failed.");
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
  const response = await fetch(
    `${apiBaseUrl}/batches?offset=${offset}&limit=${limit}`,
    { credentials: "include" },
  );
  if (!response.ok) throw new Error("Unable to load batches.");
  return response.json() as Promise<Batch[]>;
}
