"use client";

import { useEffect, useState } from "react";

import { getBatches } from "@/services/batches";
import type { Batch } from "@/types/batch";

const activeStatuses = new Set(["UPLOADING", "QUEUED", "PROCESSING"]);
const pageSize = 8;

export function BatchOverview() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(showLoading = false) {
    if (showLoading) setLoading(true);
    try {
      setBatches(await getBatches(page * pageSize, pageSize));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load batches.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(true);
    const timer = window.setInterval(() => { void load(); }, 5000);
    return () => window.clearInterval(timer);
  }, [page]);

  const active = batches.filter((batch) => activeStatuses.has(batch.status)).length;
  return <section className="panel" aria-labelledby="batch-title">
    <div className="section-heading">
      <div><p className="eyebrow">Operations</p><h2 id="batch-title">Batches</h2></div>
      <span className={active ? "badge active" : "badge"}>{active ? `${active} in progress` : "All caught up"}</span>
    </div>
    {error && <p className="error" role="alert">{error}</p>}
    {loading ? <p className="muted" role="status">Loading batches…</p> : batches.length === 0 ? <p className="muted">No batches on this page.</p> : <div className="table-wrap">
      <table><thead><tr><th>Batch</th><th>Status</th><th>Progress</th><th>Review</th></tr></thead><tbody>{batches.map((batch) => <tr key={batch.id}><td><strong>{batch.original_folder_name}</strong><small>{batch.batch_code}</small></td><td><span className="badge">{batch.status}</span></td><td>{batch.processed_images}/{batch.total_images} processed</td><td>{batch.review_count} review · {batch.failed_count} failed</td></tr>)}</tbody></table>
    </div>}
    <nav className="pagination" aria-label="Batch pages">
      <button className="secondary" type="button" onClick={() => setPage((current) => Math.max(0, current - 1))} disabled={page === 0 || loading}>Previous</button>
      <span>Page {page + 1}</span>
      <button className="secondary" type="button" onClick={() => setPage((current) => current + 1)} disabled={batches.length < pageSize || loading}>Next</button>
    </nav>
  </section>;
}
