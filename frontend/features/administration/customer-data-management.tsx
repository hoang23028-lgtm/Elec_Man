"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";

import {
  createCustomer,
  getCustomers,
  getCustomerSummary,
  getCustomerUsagePurposes,
  importCustomerFile,
  type CustomerCreateInput,
  type CustomerRecord,
  type CustomerSummary,
} from "@/services/customers";

const PAGE_SIZE = 15;
const numberFormatter = new Intl.NumberFormat("vi-VN");
const usagePurposeLabels: Record<string, string> = {
  SINH_HOAT: "Sinh hoạt",
  HO_KINH_DOANH: "Hộ kinh doanh",
  KINH_DOANH: "Kinh doanh",
  HO_SAN_XUAT: "Hộ sản xuất",
  SAN_XUAT: "Sản xuất",
  UB_HANH_CHINH: "Ủy ban / Hành chính",
  TRUONG_HOC_Y_TE: "Trường học / Y tế",
  VIETTEL: "Viettel",
  KHAC: "Khác",
};

function formatUsagePurpose(value: string) {
  return usagePurposeLabels[value] ?? value.replaceAll("_", " ").toLocaleLowerCase("vi-VN");
}
type CustomerForm = Omit<CustomerCreateInput, "initial_reading"> & {
  initial_reading: string;
};

const emptyCustomerForm = (): CustomerForm => ({
  customer_code: "",
  full_name: "",
  address: "",
  electricity_route: "",
  meter_serial: "",
  initial_reading: "",
  usage_purpose: "",
});

export function CustomerDataManagement({ csrfToken }: { csrfToken: string }) {
  const [summary, setSummary] = useState<CustomerSummary | null>(null);
  const [usagePurposes, setUsagePurposes] = useState<string[]>([]);
  const [customers, setCustomers] = useState<CustomerRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [loadingCustomers, setLoadingCustomers] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creatingCustomer, setCreatingCustomer] = useState(false);
  const [customerForm, setCustomerForm] = useState<CustomerForm>(emptyCustomerForm);
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  async function loadSummary() {
    try {
      setSummary(await getCustomerSummary());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải dữ liệu khách hàng.");
    }
  }

  useEffect(() => {
    void loadSummary();
    void getCustomerUsagePurposes()
      .then(setUsagePurposes)
      .catch((reason) => {
        setError(
          reason instanceof Error ? reason.message : "Không thể tải danh sách mục đích sử dụng.",
        );
      });
  }, []);

  const loadCustomers = useCallback(async () => {
    setLoadingCustomers(true);
    try {
      const result = await getCustomers((page - 1) * PAGE_SIZE, PAGE_SIZE, search);
      setCustomers(result.items);
      setTotal(result.total);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải danh sách khách hàng.");
    } finally {
      setLoadingCustomers(false);
    }
  }, [page, search]);

  useEffect(() => {
    void loadCustomers();
  }, [loadCustomers]);

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
      if (page === 1) await loadCustomers();
      else setPage(1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể nhập dữ liệu khách hàng.");
    } finally {
      setBusy(false);
    }
  }

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  }

  function updateCustomerField(field: keyof CustomerForm, value: string) {
    setCustomerForm((current) => ({ ...current, [field]: value }));
  }

  async function submitCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const initialReading = Number(customerForm.initial_reading);
    if (!Number.isInteger(initialReading) || initialReading < 0) {
      setError("Chỉ số khởi tạo phải là số nguyên không âm.");
      return;
    }
    setCreatingCustomer(true);
    setMessage(null);
    setError(null);
    try {
      const created = await createCustomer(
        {
          ...customerForm,
          customer_code: customerForm.customer_code.trim().toUpperCase(),
          meter_serial: customerForm.meter_serial.trim().toUpperCase(),
          initial_reading: initialReading,
        },
        csrfToken,
      );
      setMessage(`Đã thêm khách hàng ${created.customer_code} – ${created.full_name}.`);
      setCustomerForm(emptyCustomerForm());
      setShowCreateForm(false);
      setSearchInput(created.customer_code);
      setPage(1);
      setSearch(created.customer_code);
      await loadSummary();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể thêm khách hàng.");
    } finally {
      setCreatingCustomer(false);
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
        <button
          type="button"
          className={showCreateForm ? "secondary" : undefined}
          aria-expanded={showCreateForm}
          aria-controls="customer-create-form"
          onClick={() => {
            setShowCreateForm((value) => !value);
            setMessage(null);
            setError(null);
          }}
        >
          {showCreateForm ? "Đóng biểu mẫu" : "Thêm khách hàng"}
        </button>
      </div>
      <div className="summary-grid customer-summary">
        <div><strong>{summary?.total ?? "—"}</strong><span>Khách hàng</span></div>
        <div><strong>{summary?.matched_readings ?? "—"}</strong><span>Kết quả đã khớp</span></div>
        <div><strong>{summary?.unmatched_readings ?? "—"}</strong><span>Chưa tìm thấy</span></div>
      </div>

      {showCreateForm && (
        <form
          id="customer-create-form"
          className="account-editor customer-editor"
          onSubmit={submitCustomer}
          aria-busy={creatingCustomer}
        >
          <div className="account-editor-heading">
            <div>
              <p className="eyebrow">Nhập thủ công</p>
              <h3>Thêm hồ sơ khách hàng mới</h3>
              <p className="muted">Mã khách hàng và serial công tơ không được trùng.</p>
            </div>
          </div>
          <div className="customer-form-grid">
            <label>
              Mã khách hàng
              <input
                autoFocus
                value={customerForm.customer_code}
                onChange={(event) => updateCustomerField("customer_code", event.target.value)}
                placeholder="PN2.001"
                maxLength={128}
                required
              />
            </label>
            <label>
              Họ và tên
              <input
                value={customerForm.full_name}
                onChange={(event) => updateCustomerField("full_name", event.target.value)}
                maxLength={255}
                required
              />
            </label>
            <label>
              Serial công tơ
              <input
                value={customerForm.meter_serial}
                onChange={(event) => updateCustomerField("meter_serial", event.target.value)}
                placeholder="CT-2026-001"
                maxLength={128}
                required
              />
            </label>
            <label>
              Chỉ số khởi tạo
              <input
                type="number"
                value={customerForm.initial_reading}
                onChange={(event) => updateCustomerField("initial_reading", event.target.value)}
                min={0}
                max={999999999}
                step={1}
                required
              />
            </label>
            <label>
              Tuyến điện
              <input
                value={customerForm.electricity_route}
                onChange={(event) => updateCustomerField("electricity_route", event.target.value)}
                maxLength={255}
                required
              />
            </label>
            <label>
              Mục đích sử dụng
              <select
                value={customerForm.usage_purpose}
                onChange={(event) => updateCustomerField("usage_purpose", event.target.value)}
                required
              >
                <option value="" disabled>Chọn mục đích sử dụng</option>
                {usagePurposes.map((purpose) => (
                  <option key={purpose} value={purpose}>
                    {formatUsagePurpose(purpose)}
                  </option>
                ))}
              </select>
            </label>
            <label className="customer-address-field">
              Địa chỉ
              <input
                value={customerForm.address}
                onChange={(event) => updateCustomerField("address", event.target.value)}
                maxLength={500}
                required
              />
            </label>
          </div>
          <div className="customer-form-actions">
            <button
              className="secondary"
              type="button"
              disabled={creatingCustomer}
              onClick={() => {
                setCustomerForm(emptyCustomerForm());
                setShowCreateForm(false);
              }}
            >
              Hủy
            </button>
            <button type="submit" disabled={creatingCustomer}>
              {creatingCustomer ? "Đang thêm…" : "Lưu khách hàng"}
            </button>
          </div>
        </form>
      )}

      <div className="customer-import-heading">
        <strong>Nhập nhiều khách hàng từ tệp JSON</strong>
        <span className="muted">Dùng khi cần thêm hoặc cập nhật hàng loạt.</span>
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

      <div className="customer-list-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Hồ sơ trong cơ sở dữ liệu</p>
            <h3>Khách hàng đã nhập</h3>
            <p className="muted">Tra cứu theo mã, họ tên, số serial hoặc tuyến điện.</p>
          </div>
          <span className="muted">{numberFormatter.format(total)} khách hàng</span>
        </div>

        <form className="customer-search" role="search" onSubmit={applySearch}>
          <label htmlFor="customer-search">Tìm kiếm khách hàng</label>
          <div className="inline-controls">
            <input
              id="customer-search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Ví dụ: KH004, Nguyễn Văn A hoặc CT-2026-001"
              maxLength={255}
            />
            <button type="submit" disabled={loadingCustomers}>Tìm kiếm</button>
          </div>
        </form>

        <div className="table-wrap customer-table" aria-busy={loadingCustomers}>
          <table>
            <thead>
              <tr>
                <th className="row-number">STT</th>
                <th>Mã khách hàng</th>
                <th>Họ và tên</th>
                <th>Địa chỉ</th>
                <th>Tuyến điện</th>
                <th>Serial công tơ</th>
                <th>Chỉ số khởi tạo</th>
                <th>Mục đích sử dụng</th>
              </tr>
            </thead>
            <tbody>
              {loadingCustomers ? (
                <tr>
                  <td colSpan={8} className="empty-state" role="status">
                    Đang tải danh sách khách hàng…
                  </td>
                </tr>
              ) : customers.length ? (
                customers.map((customer, index) => (
                  <tr key={customer.id}>
                    <td className="row-number">{(page - 1) * PAGE_SIZE + index + 1}</td>
                    <td><strong>{customer.customer_code}</strong></td>
                    <td>{customer.full_name}</td>
                    <td>{customer.address}</td>
                    <td>{customer.electricity_route}</td>
                    <td><code>{customer.meter_serial}</code></td>
                    <td>{numberFormatter.format(customer.initial_reading)}</td>
                    <td>{formatUsagePurpose(customer.usage_purpose)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="empty-state">
                    Không tìm thấy khách hàng phù hợp. Hãy thử mã khách hàng, họ tên,
                    số serial hoặc tuyến điện khác.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <nav className="pagination" aria-label="Phân trang danh sách khách hàng">
          <button
            className="secondary"
            type="button"
            disabled={page <= 1 || loadingCustomers}
            onClick={() => setPage((value) => value - 1)}
          >
            Trang trước
          </button>
          <span>
            Trang {page} / {totalPages} · {numberFormatter.format(total)} khách hàng
          </span>
          <button
            className="secondary"
            type="button"
            disabled={page >= totalPages || loadingCustomers}
            onClick={() => setPage((value) => value + 1)}
          >
            Trang sau
          </button>
        </nav>
      </div>
    </section>
  );
}
