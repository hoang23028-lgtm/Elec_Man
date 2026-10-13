const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export type PageData<T> = { items: T[]; total: number };

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); }
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  fallbackMessage = "Yêu cầu thất bại.",
): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, { ...init, credentials: "include" });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Không thể kết nối máy chủ. Hãy kiểm tra mạng và thử lại.", 0);
  }
  if (response.ok) return response;
  if (response.status === 401 && path !== "/auth/login" && path !== "/auth/session" && typeof window !== "undefined") {
    window.dispatchEvent(new Event("session-expired"));
  }
  const body: { detail?: unknown } = await response.json().catch(() => ({}));
  throw new ApiError(typeof body.detail === "string" ? body.detail : fallbackMessage, response.status);
}

export async function apiJson<T>(
  path: string,
  init: RequestInit = {},
  fallbackMessage?: string,
): Promise<T> {
  const response = await apiFetch(path, init, fallbackMessage);
  try { return await response.json() as T; }
  catch { throw new ApiError("Phản hồi máy chủ không hợp lệ. Hãy tải lại dữ liệu.", response.status); }
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
