import type { LoginInput, LoginResult } from "@/types/auth";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export async function login(input: LoginInput): Promise<LoginResult> {
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body: { detail?: string } = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Không thể đăng nhập.");
  }
  return response.json() as Promise<LoginResult>;
}

export async function logout(csrfToken: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRF-Token": csrfToken },
  });
  if (!response.ok) throw new Error("Không thể đăng xuất.");
}
