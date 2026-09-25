import type {
  LoginInput,
  LoginResult,
  RegistrationInput,
  RegistrationResult,
} from "@/types/auth";
import { apiFetch, apiJson } from "@/services/http";

export type CurrentUser = {
  id: string;
  username: string;
  last_login_at: string | null;
};

export async function login(input: LoginInput): Promise<LoginResult> {
  return apiJson<LoginResult>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }, "Không thể đăng nhập.");
}

export async function registerAccount(
  input: RegistrationInput,
): Promise<RegistrationResult> {
  return apiJson<RegistrationResult>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }, "Không thể gửi yêu cầu đăng ký.");
}

export async function logout(csrfToken: string): Promise<void> {
  await apiFetch("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  }, "Không thể đăng xuất.");
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiJson<CurrentUser>("/auth/me", {}, "Không thể xác định tài khoản hiện tại.");
}
