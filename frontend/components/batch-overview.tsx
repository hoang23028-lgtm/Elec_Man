"use client";

import { useEffect, useState } from "react";

import { getBatches } from "@/services/batches";
import type { Batch } from "@/types/batch";

const activeStatuses = new Set(["UPLOADING", "QUEUED", "PROCESSING"]);

export function BatchOverview() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try { setBatches(await getBatches()); setError(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load batches."); }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => { void load(); }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  const active = batches.filter((batch) => activeStatuses.has(batch.status)).length;
  return <section className="panel" aria-labelledby="batch-title"><div className="section-heading"><div><p className="eyebrow">Operations</p><h2 id="batch-title">Batches</h2></div><span className={active ? "badge active" : "badge"}>{active ? `${active} in progress` : "All caught up"}</span></div>{error && <p className="error" role="alert">{error}</p>}{batches.length === 0 ? <p className="muted">No batches have been created.</p> : <div className="table-wrap"><table><thead><tr><th>Batch</th><th>Status</th><th>Progress</th><th>Review</th></tr></thead><tbody>{batches.slice(0, 8).map((batch) => <tr key={batch.id}><td><strong>{batch.original_folder_name}</strong><small>{batch.batch_code}</small></td><td><span className="badge">{batch.status}</span></td><td>{batch.processed_images}/{batch.total_images} processed</td><td>{batch.review_count} review · {batch.failed_count} failed</td></tr>)}</tbody></table></div>}</section>;
}
