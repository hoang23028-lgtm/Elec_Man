export type LoginInput = { username: string; password: string };
export type LoginResult = { csrf_token: string; expires_at: string };
export type RegistrationInput = { username: string; password: string };
export type RegistrationFormInput = RegistrationInput & { confirmPassword: string };
export type RegistrationResult = { message: string };
