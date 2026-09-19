import { paginatedJson } from "@/services/http";

export type AuditRow = {
  id: string;
  username: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  ip_address: string | null;
  created_at: string;
};

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
  return paginatedJson<AuditRow>(
    `/audit?${params.toString()}`,
    "Không thể tải lịch sử kiểm toán.",
  );
}
