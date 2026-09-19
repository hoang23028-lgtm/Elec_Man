"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { getResults, reviewResult, type Result } from "@/services/results";
import { exportConfirmed } from "@/services/system";

type Draft = { customer: string; reading: string };
type Props = { csrfToken: string; refreshKey?: number };

const pageSize = 12;

function initialDraft(row: Result): Draft {
  return {
    customer: row.final_customer_id ?? row.customer_id_ai ?? "",
    reading: row.final_meter_reading ?? row.meter_reading_ai ?? "",
  };
}

function confidenceLabel(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function OperationsResults({ csrfToken, refreshKey = 0 }: Props) {
  const [pending, setPending] = useState<Result[]>([]);
  const [confirmed, setConfirmed] = useState<Result[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [pendingPage, setPendingPage] = useState(0);
  const [confirmedPage, setConfirmedPage] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(
    async (showLoading = true) => {
      if (showLoading) setLoading(true);
      try {
        const [nextPending, nextConfirmed] = await Promise.all([
          getResults({
            imageStatus: "REVIEW_REQUIRED",
            offset: pendingPage * pageSize,
            limit: pageSize,
            search,
          }),
          getResults({
            imageStatus: "CONFIRMED",
            offset: confirmedPage * pageSize,
            limit: pageSize,
            search,
          }),
        ]);
        setPending(nextPending);
        setConfirmed(nextConfirmed);
        setDrafts((current) => {
          const next = { ...current };
          for (const row of [...nextPending, ...nextConfirmed]) {
            if (!next[row.image_id]) next[row.image_id] = initialDraft(row);
          }
          return next;
        });
        setError(null);
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Không thể tải dữ liệu vận hành.",
        );
      } finally {
        if (showLoading) setLoading(false);
      }
    },
    [confirmedPage, pendingPage, search],
  );

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(false), 5000);
    return () => window.clearInterval(timer);
  }, [load, refreshKey]);

  function updateDraft(id: string, field: keyof Draft, value: string) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...(current[id] ?? { customer: "", reading: "" }), [field]: value },
    }));
  }

  async function submitReview(row: Result, action: "CONFIRM" | "REJECT") {
    const draft = drafts[row.image_id] ?? initialDraft(row);
    setBusyId(row.image_id);
    setError(null);
    setMessage(null);
    try {
      await reviewResult(
        row.image_id,
        csrfToken,
        action,
        draft.customer.trim(),
        draft.reading.trim(),
      );
      setMessage(
        action === "CONFIRM"
          ? "Đã xác nhận kết quả và lưu nhật ký thay đổi."
          : "Đã từ chối kết quả và lưu vào nhật ký.",
      );
      setDrafts((current) => {
        const next = { ...current };
        delete next[row.image_id];
        return next;
      });
      await load(false);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể lưu kết quả.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function download() {
    setExporting(true);
    setError(null);
    try {
      window.location.assign(await exportConfirmed(csrfToken));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể tạo tệp Excel.",
      );
    } finally {
      setExporting(false);
    }
  }

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPendingPage(0);
    setConfirmedPage(0);
    setSearch(searchInput.trim());
  }

  function renderCard(row: Result, editableConfirmed = false) {
    const draft = drafts[row.image_id] ?? initialDraft(row);
    const busy = busyId === row.image_id;
    return (
      <article className="result-card" key={row.image_id}>
        <a
          className="result-preview"
          href={`/api/v1/images/${row.image_id}/preview`}
          target="_blank"
          rel="noreferrer"
          aria-label={`Mở ảnh ${row.original_filename}`}
        >
          <img
            src={`/api/v1/images/${row.image_id}/preview`}
            alt={`Ảnh đồng hồ ${row.original_filename}`}
            loading="lazy"
          />
        </a>
        <div className="result-card-body">
          <div className="result-card-heading">
            <div>
              <strong title={row.original_filename}>{row.original_filename}</strong>
              <small>Mã ảnh: {row.image_id.slice(0, 8)}</small>
            </div>
            <span
              className={`badge ${row.final_confidence > 0.9 ? "active" : "warning"}`}
            >
              {confidenceLabel(row.final_confidence)}
            </span>
          </div>
          {editableConfirmed && (
            <span className="result-origin">
              {row.auto_confirmed ? "AI tự động xác nhận" : "Đã kiểm duyệt thủ công"}
            </span>
          )}
          <div className="result-fields">
            <label>
              Mã khách hàng
              <input
                value={draft.customer}
                onChange={(event) =>
                  updateDraft(row.image_id, "customer", event.target.value)
                }
                disabled={busy}
              />
            </label>
            <label>
              Số điện (kWh)
              <input
                value={draft.reading}
                onChange={(event) =>
                  updateDraft(row.image_id, "reading", event.target.value)
                }
                disabled={busy}
              />
            </label>
          </div>
          <div className="result-actions">
            {editableConfirmed ? (
              <button
                type="button"
                onClick={() => void submitReview(row, "CONFIRM")}
                disabled={busy || !draft.customer.trim() || !draft.reading.trim()}
              >
                {busy ? "Đang lưu…" : "Lưu thay đổi"}
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => void submitReview(row, "CONFIRM")}
                  disabled={busy || !draft.customer.trim() || !draft.reading.trim()}
                >
                  {busy ? "Đang lưu…" : "Xác nhận"}
                </button>
                <button
                  className="danger"
                  type="button"
                  onClick={() => void submitReview(row, "REJECT")}
                  disabled={busy}
                >
                  Từ chối
                </button>
              </>
            )}
          </div>
        </div>
      </article>
    );
  }

  return (
    <section className="panel full-span operations-results" aria-labelledby="operations-results-title">
      <div className="section-heading operations-results-heading">
        <div>
          <p className="eyebrow">Bước 3</p>
          <h2 id="operations-results-title">Kết quả xử lý</h2>
          <p className="muted">
            Kết quả có độ tin cậy trên 90% được tự động xác nhận. Mọi chỉnh sửa
            sau xác nhận đều được lưu vào nhật ký truy vết.
          </p>
        </div>
        <button className="secondary" type="button" onClick={() => void load()} disabled={loading}>
          Làm mới
        </button>
      </div>
      <form className="operations-search" onSubmit={applySearch} role="search">
        <label htmlFor="operations-result-search">Tìm theo tên ảnh, mã khách hàng hoặc số điện</label>
        <div className="inline-controls">
          <input
            id="operations-result-search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Ví dụ: KH004 hoặc 63751"
          />
          <button type="submit" className="secondary">Tìm kiếm</button>
        </div>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="notice" role="status">{message}</p>}
      <div className="review-board" aria-busy={loading}>
        <section className="review-lane needs-review" aria-labelledby="needs-review-title">
          <div className="review-lane-heading">
            <div>
              <p className="eyebrow">Cần xử lý</p>
              <h3 id="needs-review-title">Chờ kiểm duyệt</h3>
            </div>
            <span className="lane-count" aria-label={`${pending.length} kết quả trên trang`}>
              {pending.length}
            </span>
          </div>
          {loading && !pending.length ? (
            <p className="empty-state" role="status">Đang tải hàng chờ…</p>
          ) : pending.length ? (
            <div className="result-list">{pending.map((row) => renderCard(row))}</div>
          ) : (
            <p className="empty-state">Không có kết quả nào cần kiểm duyệt.</p>
          )}
          <nav className="pagination" aria-label="Phân trang hàng chờ kiểm duyệt">
            <button className="secondary" type="button" onClick={() => setPendingPage((page) => Math.max(0, page - 1))} disabled={!pendingPage || loading}>Trước</button>
            <span>Trang {pendingPage + 1}</span>
            <button className="secondary" type="button" onClick={() => setPendingPage((page) => page + 1)} disabled={pending.length < pageSize || loading}>Sau</button>
          </nav>
        </section>
        <section className="review-lane confirmed-lane" aria-labelledby="confirmed-title">
          <div className="review-lane-heading">
            <div>
              <p className="eyebrow">Hoàn tất</p>
              <h3 id="confirmed-title">Đã xác nhận</h3>
            </div>
            <span className="lane-count success" aria-label={`${confirmed.length} kết quả trên trang`}>
              {confirmed.length}
            </span>
          </div>
          {loading && !confirmed.length ? (
            <p className="empty-state" role="status">Đang tải kết quả…</p>
          ) : confirmed.length ? (
            <div className="result-list">{confirmed.map((row) => renderCard(row, true))}</div>
          ) : (
            <p className="empty-state">Chưa có kết quả nào được xác nhận.</p>
          )}
          <nav className="pagination" aria-label="Phân trang kết quả đã xác nhận">
            <button className="secondary" type="button" onClick={() => setConfirmedPage((page) => Math.max(0, page - 1))} disabled={!confirmedPage || loading}>Trước</button>
            <span>Trang {confirmedPage + 1}</span>
            <button className="secondary" type="button" onClick={() => setConfirmedPage((page) => page + 1)} disabled={confirmed.length < pageSize || loading}>Sau</button>
          </nav>
          <div className="export-confirmed">
            <div>
              <strong>Tải danh sách đã kiểm duyệt</strong>
              <p className="muted">Tệp Excel bao gồm toàn bộ kết quả đã xác nhận.</p>
            </div>
            <button type="button" onClick={() => void download()} disabled={exporting}>
              {exporting ? "Đang tạo Excel…" : "Tải file Excel"}
            </button>
          </div>
        </section>
      </div>
    </section>
  );
}
