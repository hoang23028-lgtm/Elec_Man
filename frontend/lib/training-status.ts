const labels: Record<string, string> = {
  PENDING: "Đang chờ",
  RUNNING: "Đang huấn luyện",
  COMPLETED: "Hoàn tất",
  FAILED: "Thất bại",
  CANCELLED: "Đã hủy",
};

export function trainingStatusLabel(status: string): string {
  return labels[status] ?? "Chưa rõ trạng thái";
}
