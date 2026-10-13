export type LoginInput = { username: string; password: string };
export type UserRole = "SUPER_ADMIN" | "ADMIN" | "VIEWER";
export const roleLabels: Record<UserRole, string> = {
  SUPER_ADMIN: "Quản trị toàn hệ thống",
  ADMIN: "Quản trị vận hành",
  VIEWER: "Người xem",
};
export function canOperate(role: UserRole | null): boolean {
  return role === "ADMIN" || role === "SUPER_ADMIN";
}
export function canAccessPage(role: UserRole | null, page: string): boolean {
  if (page === "dashboard") return true;
  if (page === "model-lifecycle" || page === "traceability") return role === "SUPER_ADMIN";
  return ["operations", "batches", "administration"].includes(page) && canOperate(role);
}
export type LoginResult = { csrf_token: string; expires_at: string; username: string; role: UserRole };
export type RegistrationInput = { username: string; password: string };
export type RegistrationFormInput = RegistrationInput & { confirmPassword: string };
export type RegistrationResult = { message: string };
