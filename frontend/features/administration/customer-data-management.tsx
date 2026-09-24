"use client";

import { ChangeEvent, useEffect, useState } from "react";

import {
  getCustomerSummary,
  importCustomerFile,
  type CustomerSummary,
} from "@/services/customers";

export function CustomerDataManagement({ csrfToken }: { csrfToken: string }) {
  const [summary, setSummary] = useState<CustomerSummary | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadSummary() {
    try {
      setSummary(await getCustomerSummary());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải dữ liệu khách hàng.");
    }
  }

  useEffect(() => {
    void loadSummary();
  }, []);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setMessage(null);
    setError(null);
    if (selected && !selected.name.toLowerCase().endsWith(".json")) {
      setFile(null);
      setError("Chỉ chấp nhận tệp JSON.");
      return;
    }
    if (selected && selected.size > 10 * 1024 * 1024) {
      setFile(null);
      setError("Tệp dữ liệu khách hàng không được vượt quá 10 MB.");
      return;
    }
    setFile(selected);
  }

  async function upload() {
    if (!file) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await importCustomerFile(file, csrfToken);
      setMessage(
        `Đã nhập ${result.total} khách hàng: thêm ${result.created}, cập nhật ${result.updated}, đối chiếu lại ${result.reconciled_readings} kết quả.`,
      );
      setFile(null);
      setFileInputKey((value) => value + 1);
      await loadSummary();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể nhập dữ liệu khách hàng.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="panel full-span"
      aria-labelledby="customer-data-title"
      aria-busy={busy}
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dữ liệu đối chiếu</p>
          <h2 id="customer-data-title">Danh sách khách hàng</h2>
          <p className="muted">
            Nhập tệp JSON theo mẫu để đối chiếu mã khách hàng OCR với hồ sơ và số serial công tơ.
          </p>
        </div>
      </div>
      <div className="summary-grid customer-summary">
        <div><strong>{summary?.total ?? "—"}</strong><span>Khách hàng</span></div>
        <div><strong>{summary?.matched_readings ?? "—"}</strong><span>Kết quả đã khớp</span></div>
        <div><strong>{summary?.unmatched_readings ?? "—"}</strong><span>Chưa tìm thấy</span></div>
      </div>
      <div className="inline-controls customer-import-controls">
        <input
          key={fileInputKey}
          type="file"
          accept="application/json,.json"
          onChange={chooseFile}
          disabled={busy}
          aria-describedby="customer-file-help"
        />
        <button type="button" onClick={() => void upload()} disabled={!file || busy}>
          {busy ? "Đang nhập…" : "Nhập dữ liệu khách hàng"}
        </button>
      </div>
      <p id="customer-file-help" className="muted">
        Tệp JSON tối đa 10 MB và 10.000 khách hàng.
        {file ? ` Đã chọn: ${file.name}` : ""}
      </p>
      {message && <p className="notice" role="status">{message}</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
