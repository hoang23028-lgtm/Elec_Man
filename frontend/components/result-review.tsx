"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { getResultsPage, reviewResult, type Result } from "@/services/results";

type Draft = { customer: string; reading: string };
const pageSize = 10;

export function ResultReview({ csrfToken }: { csrfToken: string }) {
  const [rows, setRows] = useState<Result[]>([]);
  const [total, setTotal] = useState(0);
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
      const result = await getResultsPage({
        offset: page * pageSize,
        limit: pageSize,
        imageStatus: status,
        search,
      });
      const next = result.items;
      setRows(next);
      setTotal(result.total);
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
        reason instanceof Error ? reason.message : "Không thể tải kết quả.",
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
      setError("Hãy nhập mã khách hàng và chỉ số điện trước khi xác nhận.");
      return;
    }
    if (
      action === "REJECT" &&
      !window.confirm(`Từ chối kết quả AI của ảnh ${row.original_filename}?`)
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
          ? "Kết quả đã được xác nhận và lưu."
          : "Kết quả đã bị từ chối và được ghi nhận.",
      );
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Kiểm duyệt thất bại.",
      );
    } finally {
      setSaving(null);
    }
  }

  return (
    <section className="panel" aria-labelledby="review-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Kiểm duyệt thủ công</p>
          <h2 id="review-title">Chỉ số đồng hồ điện</h2>
        </div>
        <button
          className="secondary"
          type="button"
          onClick={() => void load(true)}
          disabled={loading}
        >
          Làm mới
        </button>
      </div>
      <p className="muted">
        Tìm kiếm và lọc kết quả AI, sửa các giá trị chưa chắc chắn rồi xác nhận
        hoặc từ chối từng kết quả.
      </p>
      <div className="table-tools">
        <form className="search-form" role="search" onSubmit={applySearch}>
          <label htmlFor="result-search">Tìm kiếm kết quả</label>
          <div className="inline-controls">
            <input
              id="result-search"
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Tên tệp, mã khách hàng, chỉ số điện"
            />
            <button type="submit">Tìm kiếm</button>
          </div>
        </form>
        <div>
          <label htmlFor="result-status">Trạng thái ảnh</label>
          <select
            id="result-status"
            value={status}
            onChange={(event) => {
              setPage(0);
              setStatus(event.target.value);
            }}
          >
            <option value="">Tất cả trạng thái</option>
            <option value="REVIEW_REQUIRED">Cần kiểm duyệt</option>
            <option value="CONFIRMED">Đã xác nhận</option>
            <option value="REJECTED">Đã từ chối</option>
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
          Đang tải chỉ số đồng hồ…
        </p>
      ) : rows.length === 0 ? (
        <p className="muted">Không có kết quả phù hợp với bộ lọc hiện tại.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Hình ảnh</th>
                <th>Mã khách hàng</th>
                <th>Chỉ số điện</th>
                <th>Độ tin cậy</th>
                <th>Trạng thái</th>
                <th>Quyết định</th>
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
                    ? "Đã xác nhận"
                    : row.review_status === "REJECTED"
                      ? "Đã từ chối"
                      : "Cần kiểm duyệt";
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
                      <small>Đề xuất của AI · nhấp để xem ảnh</small>
                    </td>
                    <td>
                      <input
                        aria-label={`Mã khách hàng của ${row.original_filename}`}
                        value={draft.customer}
                        onChange={(event) =>
                          updateDraft(
                            row.image_id,
                            "customer",
                            event.target.value,
                          )
                        }
                        placeholder="Ví dụ: KH004"
                        disabled={busy}
                      />
                    </td>
                    <td>
                      <input
                        inputMode="decimal"
                        aria-label={`Chỉ số điện của ${row.original_filename}`}
                        value={draft.reading}
                        onChange={(event) =>
                          updateDraft(
                            row.image_id,
                            "reading",
                            event.target.value,
                          )
                        }
                        placeholder="Ví dụ: 63751.3"
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
                        {busy ? "Đang lưu…" : "Xác nhận"}
                      </button>
                      <button
                        className="danger"
                        type="button"
                        onClick={() => void act(row, "REJECT")}
                        disabled={busy}
                      >
                        {busy ? "Đang lưu…" : "Từ chối"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <nav className="pagination" aria-label="Phân trang chỉ số đồng hồ">
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => Math.max(0, current - 1))}
          disabled={page === 0 || loading}
        >
          Trước
        </button>
        <span>
          Trang {page + 1} / {Math.max(1, Math.ceil(total / pageSize))}
        </span>
        <button
          className="secondary"
          type="button"
          onClick={() => setPage((current) => current + 1)}
          disabled={page + 1 >= Math.max(1, Math.ceil(total / pageSize)) || loading}
        >
          Sau
        </button>
      </nav>
    </section>
  );
}
