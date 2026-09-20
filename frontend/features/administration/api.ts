import { apiFetch, apiJson, paginatedJson } from "@/services/http";
import type {
  UserAccount,
  UserCreateInput,
  UserUpdateInput,
} from "@/features/administration/types";

export async function getUsers(
  offset: number,
  limit: number,
  search: string,
) {
  const query = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  if (search) query.set("search", search);
  return paginatedJson<UserAccount>(
    `/users?${query}`,
    "Không thể tải danh sách tài khoản.",
  );
}

export async function createUser(
  input: UserCreateInput,
  csrfToken: string,
) {
  return apiJson<UserAccount>(
    "/users",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(input),
    },
    "Không thể tạo tài khoản.",
  );
}

export async function updateUser(
  id: string,
  input: UserUpdateInput,
  csrfToken: string,
) {
  return apiJson<UserAccount>(
    `/users/${id}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(input),
    },
    "Không thể cập nhật tài khoản.",
  );
}

export async function changeUserPassword(
  id: string,
  newPassword: string,
  csrfToken: string,
) {
  await apiFetch(
    `/users/${id}/password`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({ new_password: newPassword }),
    },
    "Không thể đổi mật khẩu.",
  );
}

export async function deleteUser(id: string, csrfToken: string) {
  await apiFetch(
    `/users/${id}`,
    {
      method: "DELETE",
      headers: { "X-CSRF-Token": csrfToken },
    },
    "Không thể xóa tài khoản.",
  );
}
