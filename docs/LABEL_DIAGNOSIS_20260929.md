# Chẩn đoán nhãn công tơ ngày 29/09/2026

Đọc dữ liệu đang chạy: 61 ảnh, 37 ảnh có nhãn chỉ số và vùng dãy số do người dùng
lưu; chưa có nhãn vùng toàn bộ công tơ hoặc mã khách hàng. Các nhãn bao phủ 0–9.
Pipeline đầy đủ hiện yêu cầu 200 mẫu; số mẫu đủ điều kiện hiện tại là 0.

## So sánh trên 37 vùng đã khoanh

| Bộ đọc | Đúng toàn chuỗi | Sai | Không đọc được | Trung vị thời gian đọc |
|---|---:|---:|---:|---:|
| Cơ sở, fallback giới hạn | 9/37 (24,3%) | 17 | 11 | 2.240 ms |
| Thử nghiệm đọc toàn chuỗi | 19/37 (51,4%) | 2 | 16 | 29 ms |

Không có lỗi thực thi. Bộ thử nghiệm trả lời 21 ảnh, đúng 19 ảnh trong số đó;
không được gọi 90,5% này là độ chính xác trên toàn bộ dữ liệu. Nó từ chối nhiều
ảnh hơn. Thời gian chỉ tính bộ đọc, không tính hàng đợi, giải mã, cắt ảnh hoặc mạng.

## Giới hạn và quyết định

- Vùng được con người cung cấp, số ô lấy theo độ dài nhãn. Không đánh giá khả năng
  tự tìm công tơ hay vùng chỉ số.
- Đây là chẩn đoán tập thu thập, không phải test độc lập. Chưa biết nhóm công tơ,
  không thể đảm bảo tách công tơ giữa train/test. Nhãn được dùng như đáp án người
  dùng cung cấp, chưa được đánh giá độc lập lần hai.
- Giữ nguyên nhãn, dữ liệu chính thức và mô hình vận hành; chưa kích hoạt bộ thử
  nghiệm, không hạ ngưỡng mẫu để ép chạy huấn luyện.
- Tiếp theo: kiểm tra các ảnh sai/không đọc được, bổ sung nhóm công tơ để chia tập;
  dành riêng test trước khi fine-tune. Nếu huấn luyện đủ các bước, bổ sung vùng
  toàn bộ công tơ; nếu chỉ cải thiện đọc số, tách pipeline reader-only để tận dụng
  nhãn hiện có mà không phụ thuộc nhãn định vị toàn công tơ.

Báo cáo chi tiết nằm tại `logs/reader-evaluation/labels-20260929.json` (gitignore,
không công khai vì chứa nhãn và ID ảnh). Chạy lại với `python -m ai.diagnose_labels`
và đường dẫn đầu ra mới trong môi trường có dependency/cấu hình AI và backend.
