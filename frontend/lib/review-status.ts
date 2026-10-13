export function readingLabelStatus(
  reviewStatus: string | null,
  storedReading: string | null,
  draftReading: string,
): string {
  if (!draftReading) return "Chưa nhập";
  if (draftReading !== (storedReading ?? "")) return "Chưa lưu nhãn";
  if (reviewStatus === "CONFIRMED") return "Đã xác nhận";
  if (reviewStatus === "LABELED") return "Đã lưu nhãn";
  if (reviewStatus === "REJECTED") return "Đã từ chối";
  return "AI đề xuất · chưa lưu nhãn";
}
