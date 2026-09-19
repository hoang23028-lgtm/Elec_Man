import { apiJson } from "@/services/http";
export type Dashboard = {
  batches: number;
  images: number;
  jobs: Record<string, number>;
};
export async function getDashboard(): Promise<Dashboard> {
  return apiJson<Dashboard>("/dashboard", {}, "Không thể tải bảng điều khiển.");
}
export async function exportConfirmed(csrfToken: string): Promise<string> {
  const body = await apiJson<{ download_url: string }>("/exports/final", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  }, "Không thể tạo tệp Excel.");
  return body.download_url;
}
