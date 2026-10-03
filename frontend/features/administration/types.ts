export type UserAccount = {
  id: string;
  username: string;
  is_active: boolean;
  role: "ADMIN" | "VIEWER";
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
};

export type UserCreateInput = {
  username: string;
  password: string;
  is_active: boolean;
  role?: "ADMIN" | "VIEWER";
};

export type UserUpdateInput = {
  username?: string;
  is_active?: boolean;
  role?: "ADMIN" | "VIEWER";
};
