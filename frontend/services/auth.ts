import type { LoginInput, LoginResult } from "@/types/auth";
import { apiFetch, apiJson } from "@/services/http";

export async function login(input: LoginInput): Promise<LoginResult> {
  return apiJson<LoginResult>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }, "Không thể đăng nhập.");
}

export async function logout(csrfToken: string): Promise<void> {
  await apiFetch("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  }, "Không thể đăng xuất.");
}
