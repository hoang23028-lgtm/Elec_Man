"use client";

import { useEffect, useState } from "react";

import { getAuditLogs, type AuditRow } from "@/services/audit";

const pageSize = 10;
const actions = ["", "LOGIN_SUCCESS", "LOGIN_FAILED", "CREATE_BATCH", "UPLOAD_IMAGE", "START_BATCH", "CONFIRM_RESULT", "REJECT_RESULT", "EXPORT_EXCEL", "LOGOUT"];

export function AuditHistory() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [action, setAction] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setRows(await getAuditLogs(page * pageSize, pageSize, action));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load audit history.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [action, page]);

  return <section className="panel full-span" aria-labelledby="audit-title">
    <div className="section-heading">
      <div><p className="eyebrow">Traceability</p><h2 id="audit-title">Audit history</h2></div>
      <button className="secondary" type="button" onClick={() => void load()} disabled={loading}>Refresh</button>
    </div>
    <div className="audit-filter"><label htmlFor="audit-action">Action</label><select id="audit-action" value={action} onChange={(event) => { setPage(0); setAction(event.target.value); }}>{actions.map((item) => <option key={item || "ALL"} value={item}>{item || "All actions"}</option>)}</select></div>
    {error && <p className="error" role="alert">{error}</p>}
    {loading ? <p className="muted" role="status">Loading audit history…</p> : rows.length === 0 ? <p className="muted">No audit events match this filter.</p> : <div className="table-wrap"><table><thead><tr><th>Time</th><th>Action</th><th>User</th><th>Target</th><th>IP address</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td><span className="badge">{row.action}</span></td><td>{row.username ?? "System"}</td><td>{row.target_type ?? "—"}<small>{row.target_id ?? ""}</small></td><td>{row.ip_address ?? "—"}</td></tr>)}</tbody></table></div>}
    <nav className="pagination" aria-label="Audit history pages"><button className="secondary" type="button" onClick={() => setPage((current) => Math.max(0, current - 1))} disabled={page === 0 || loading}>Previous</button><span>Page {page + 1}</span><button className="secondary" type="button" onClick={() => setPage((current) => current + 1)} disabled={rows.length < pageSize || loading}>Next</button></nav>
  </section>;
}
