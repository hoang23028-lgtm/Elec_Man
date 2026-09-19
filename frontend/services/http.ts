const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export type PageData<T> = { items: T[]; total: number };

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  fallbackMessage = "Yêu cầu thất bại.",
): Promise<Response> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
  });
  if (response.ok) return response;
  const body: { detail?: string } = await response.json().catch(() => ({}));
  throw new Error(body.detail ?? fallbackMessage);
}

export async function apiJson<T>(
  path: string,
  init: RequestInit = {},
  fallbackMessage?: string,
): Promise<T> {
  return (await apiFetch(path, init, fallbackMessage)).json() as Promise<T>;
}

export async function paginatedJson<T>(
  path: string,
  fallbackMessage: string,
): Promise<PageData<T>> {
  const response = await apiFetch(path, {}, fallbackMessage);
  return {
    items: (await response.json()) as T[],
    total: Number(response.headers.get("X-Total-Count") ?? 0),
  };
}
