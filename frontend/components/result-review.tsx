"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { getResults, reviewResult, type Result } from "@/services/results";

type Draft = { customer: string; reading: string };
const pageSize = 10;

export function ResultReview({ csrfToken }: { csrfToken: string }) {
  const [rows, setRows] = useState<Result[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);

  async function load(showLoading = false) {
    if (showLoading) setLoading(true);
    try {
      const next = await getResults({
        offset: page * pageSize,
        limit: pageSize,
        imageStatus: status,
        search,
      });
      setRows(next);
      setDrafts((current) =>
        Object.fromEntries(
          next.map((row) => [
            row.image_id,
            current[row.image_id] ?? {
              customer: row.final_customer_id ?? row.customer_id_ai ?? "",
              reading: row.final_meter_reading ?? row.meter_reading_ai ?? "",
            },
          ]),
        ),
      );
      setError(null);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to load results.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(true);
    const timer = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [page, search, status]);

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(0);
    setSearch(searchInput.trim());
  }

  function updateDraft(id: string, key: keyof Draft, value: string) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...(current[id] ?? { customer: "", reading: "" }), [key]: value },
    }));
  }

  async function act(row: Result, action: "CONFIRM" | "REJECT") {
    const draft = drafts[row.image_id] ?? { customer: "", reading: "" };
    if (
      action === "CONFIRM" &&
      (!draft.customer.trim() || !draft.reading.trim())
    ) {
      setError("Enter both customer ID and meter reading before confirming.");
      return;
    }
    if (
      action === "REJECT" &&
      !window.confirm(`Reject the AI result for ${row.original_filename}?`)
    )
      return;
    setSaving(row.image_id);
    setError(null);
    setNotice(null);
    try {
      await reviewResult(
        row.image_id,
        csrfToken,
        action,
        draft.customer.trim(),
        draft.reading.trim(),
      );
      setNotice(
        action === "CONFIRM"
          ? "Result confirmed and saved."
          : "Result rejected and recorded.",
      );
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Review failed.");
    } finally {
      setSaving(null);
    }
  }

  return (
    <section className="panel" aria-labelledby="review-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Human review</p>
          <h2 id="review-title">Meter readings</h2>
        </div>
        <button
          className="secondary"
          type="button"
          onClick={() => void load(true)}
          disabled={loading}
        >
          Refresh
        </button>
      </div>
      <p className="muted">
        Search and filter AI suggestions, correct uncertain values, then confirm
        or reject each result.
      </p>
      <div className="table-tools">
        <form className="search-form" role="search" onSubmit={applySearch}>
          <label htmlFor="result-search">Search results</label>
          <div className="inline-controls">
            <input
              id="result-search"
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Filename, customer ID, reading"
            />
            <button type="submit">Search</button>
          </div>
        </form>
        <div>
          <label htmlFor="result-status">Image status</label>
          <select
            id="result-status"
            value={status}
            onChange={(event) => {
              setPage(0);
              setStatus(event.target.value);
            }}
          >
            <option value="">All statuses</option>
            <option value="REVIEW_REQUIRED">Needs review</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {loading ? (
        <p className="muted" role="status">
          Loading meter readings…
        </p>
      ) : rows.length === 0 ? (
        <p className="muted">No results match the current filters.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Image</th>
                <th>Customer ID</th>
                <th>Meter reading</th>
                <th>Confidence</th>
                <th>State</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const draft = drafts[row.image_id] ?? {
                  customer: "",
                  reading: "",
                };
                const busy = saving === row.image_id;
                const state =
                  row.review_status === "CONFIRMED"
                    ? "Confirmed"
                    : row.review_status === "REJECTED"
                      ? "Rejected"
                      : "Needs review";
                const confidence = Math.round(row.final_confidence * 100);
                return (
                  <tr key={row.image_id}>
                    <td>
                      <a
                        href={`/api/v1/images/${row.image_id}/preview`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {row.original_filename}
                      </a>
                      <small>AI suggestion · click to preview</small>
                    </td>
                    <td>
                      <input
                        aria-label={`Customer ID for ${row.original_filename}`}
                        value={draft.customer}
                        onChange={(event) =>
                          updateDraft(
                            row.image_id,
                            "customer",
                            event.target.value,
                          )
                        }
                        placeholder="e.g. KH004"
                        disabled={busy}
                      />
                    </td>
                    <td>
                      <input
                        inputMode="decimal"
                        aria-label={`Meter reading for ${row.original_filename}`}
                        value={draft.reading}
                        onChange={(event) =>
                          updateDraft(
                            row.image_id,
                            "reading",
                            event.target.value,
                          )
                        }
                        placeholder="e.g. 63751.3"
                        disabled={busy}
                      />
                    </td>
                    <td>
                      <span
                        className={`badge ${confidence < 80 ? "warning" : "active"}`}
                      >
                        {confidence}%
                      </span>
                    </td>
                    <td>
                      <span className="badge">{state}</span>
                    </td>
                    <td className="actions">
                      <button
                        type="button"
                        onClick={() => void act(row, "CONFIRM")}
                        disabled={busy}
                      >
                        {busy ? "Saving…" : "Confirm"}
                      </button>
                      <button
                        className="danger"
                        type="button"
                        onClick={() => void act(row, "REJECT")}
                        disabled={busy}
                      >
                        {busy ? "Saving…" : "Reject"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <nav className="pagination" aria-label="Meter reading pages">
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => Math.max(0, current - 1))}
          disabled={page === 0 || loading}
        >
          Previous
        </button>
        <span>Page {page + 1}</span>
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => current + 1)}
          disabled={rows.length < pageSize || loading}
        >
          Next
        </button>
      </nav>
    </section>
  );
}
