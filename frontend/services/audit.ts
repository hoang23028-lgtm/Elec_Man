const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export type AuditRow = {
  id: string;
  username: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  ip_address: string | null;
  created_at: string;
};

export async function getAuditLogs(
  offset = 0,
  limit = 10,
  action = "",
): Promise<AuditRow[]> {
  return (await getAuditLogsPage(offset, limit, action)).items;
}

export async function getAuditLogsPage(
  offset = 0,
  limit = 10,
  action = "",
): Promise<{ items: AuditRow[]; total: number }> {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  if (action) params.set("action", action);
  const response = await fetch(`${api}/audit?${params.toString()}`, {
    credentials: "include",
  });
  if (!response.ok) throw new Error("Không thể tải lịch sử kiểm toán.");
  return {
    items: (await response.json()) as AuditRow[],
    total: Number(response.headers.get("X-Total-Count") ?? 0),
  };
}
