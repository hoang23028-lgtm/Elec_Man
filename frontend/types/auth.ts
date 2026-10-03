export type LoginInput = { username: string; password: string };
export type UserRole = "ADMIN" | "VIEWER";
export type LoginResult = { csrf_token: string; expires_at: string; username: string; role: UserRole };
export type RegistrationInput = { username: string; password: string };
export type RegistrationFormInput = RegistrationInput & { confirmPassword: string };
export type RegistrationResult = { message: string };
