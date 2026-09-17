export type LoginInput = { username: string; password: string };
export type LoginResult = { csrf_token: string; expires_at: string };
