type PaginationProps = {
  pageIndex: number;
  totalPages: number;
  onPageChange: (pageIndex: number) => void;
  ariaLabel: string;
  disabled?: boolean;
  itemSummary?: string;
};

export function Pagination({
  pageIndex,
  totalPages,
  onPageChange,
  ariaLabel,
  disabled = false,
  itemSummary,
}: PaginationProps) {
  const pages = Math.max(1, totalPages);
  const current = Math.min(Math.max(0, pageIndex), pages - 1);

  return (
    <nav className="pagination" aria-label={ariaLabel}>
      <button
        className="secondary"
        type="button"
        onClick={() => onPageChange(current - 1)}
        disabled={current === 0 || disabled}
      >
        Trước
      </button>
      <label className="pagination-selector">
        <span>Trang</span>
        <select
          value={current + 1}
          onChange={(event) => onPageChange(Number(event.target.value) - 1)}
          disabled={disabled}
          aria-label={`Chọn trang, hiện tại trang ${current + 1} trên ${pages}`}
        >
          {Array.from({ length: pages }, (_, index) => (
            <option key={index + 1} value={index + 1}>
              {index + 1}
            </option>
          ))}
        </select>
        <span>/ {pages}{itemSummary ? ` · ${itemSummary}` : ""}</span>
      </label>
      <button
        className="secondary"
        type="button"
        onClick={() => onPageChange(current + 1)}
        disabled={current + 1 >= pages || disabled}
      >
        Sau
      </button>
    </nav>
  );
}
