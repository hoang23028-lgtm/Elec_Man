const api = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";
export type Dashboard = { batches: number; images: number; jobs: Record<string, number> };
export async function getDashboard(): Promise<Dashboard> { const response = await fetch(`${api}/dashboard`, { credentials: "include" }); if (!response.ok) throw new Error("Unable to load dashboard."); return response.json(); }
export async function exportConfirmed(csrfToken: string): Promise<string> { const response = await fetch(`${api}/exports/final`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": csrfToken } }); if (!response.ok) throw new Error("Unable to create Excel export."); const body = await response.json() as { download_url: string }; return body.download_url; }
