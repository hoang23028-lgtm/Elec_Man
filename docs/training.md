# Gắn nhãn, huấn luyện và đánh giá mô hình

## Phạm vi đã triển khai

Hệ thống **huấn luyện hai bộ định vị Ridge**, xuất crop dữ liệu chuỗi và benchmark hai reader pretrained. Không tự fine-tune trọng số PP-OCR/PARSeq; metrics ghi rõ `sequence_reader_trainable=False`. Tải thêm ảnh chưa gắn nhãn không tự biến thành dữ liệu học có giám sát.

Chỉ SUPER_ADMIN điều khiển phiên train/kích hoạt/cấu hình. ADMIN được tải ảnh và lưu nhãn trong nghiệp vụ; VIEWER không sửa dữ liệu.

## 1. Thu thập mẫu đúng

- Giữ ảnh gốc; thu thập góc chụp, ánh sáng, loại công tơ và tình huống chuyển bánh số đa dạng.
- Lưu bốn góc toàn công tơ, bốn góc vùng chỉ số và chuỗi số nguyên đúng (giữ số 0 đầu, bỏ ô đỏ).
- Bản ghi LABELED hoặc CONFIRMED có người xác nhận chỉ số và hai vùng mới đủ điều kiện pipeline định vị đầy đủ; không cần phải tạo chỉ số tháng chỉ để train.
- Chỉ lưu vùng công tơ mà chưa có vùng chỉ số/nhãn số không được tính là mẫu đầy đủ.
- SHA-256 giúp loại ảnh trùng hoàn toàn. Xác định cùng công tơ bằng mã/nhóm đã xác minh để tách train/validation, không tách ngẫu nhiên ảnh cùng công tơ vào cả hai tập.
- Nếu chưa có mã/nhóm, chia theo hash ảnh không bảo đảm độc lập theo công tơ. Registry sẽ không coi nhóm chưa xác minh là đủ điều kiện kích hoạt.

Mẫu/nhãn và tập crop nằm trong database/volume riêng, không có trên GitHub. Không chỉnh số nhãn chỉ để “đạt 200”.

## 2. Theo dõi và chạy phiên

Vòng đời mô hình → Huấn luyện: đọc mẫu đủ điều kiện/ngưỡng/mẫu mới, kiểm tra phiên PENDING/RUNNING/FAILED/COMPLETED. Mặc định 200 mẫu đầy đủ và 25 mẫu mới cho tự động; ngưỡng kỹ thuật tối thiểu 3 chỉ để ngăn dữ liệu không thể chia, **không là mức đủ chất lượng**.

Tự động train dùng chính sách đã bật và khóa advisory PostgreSQL chung để tránh tạo hai phiên đồng thời. Sau FAILED, tự động dừng; phải sửa nguyên nhân và chạy thủ công thành công trước khi tiếp tục tự động. Không tự retry train vô hạn.

Nhấn Huấn luyện ngay khi UI và server xác nhận đủ điều kiện. Theo dõi tiến độ, lỗi chung và log có run_id. Không hạ ngưỡng để ép kích hoạt bằng vài mẫu.

## 3. Những gì trainer tạo

- `meter_locator_ridge`: hồi quy bốn góc mặt công tơ.
- `reading_region_ridge`: hồi quy bốn góc vùng bộ số.
- Artifact NPZ không dùng pickle, checksum SHA-256, trạng thái TESTING.
- `sequence_datasets/<version>/`: crop đã chỉnh phối cảnh, train.tsv, validation.tsv và manifest; không nhân bản toàn bộ ảnh gốc.
- Benchmark PP-OCR/PARSeq trên crop validation: exact-match, coverage, CER. Reader không sẵn sàng thì ghi benchmark chưa thực hiện, không bịa độ chính xác.

Điểm vùng `max(0, 1 - mean_error × 4)` là điểm suy từ sai số tọa độ chuẩn hóa, **không** là mAP/IoU hay tỷ lệ đọc đúng số. Benchmark crop không đo khả năng tự định vị toàn ảnh.

## 4. Kích hoạt ứng viên

Chỉ loại model được runtime hỗ trợ, file tồn tại đúng MODELS_ROOT và checksum đúng mới được chấp nhận. Kích hoạt cần nhóm validation đã xác minh, ít nhất 30 ảnh validation và điểm vùng hợp lệ ≥0,8 cho đúng loại định vị. Gate kỹ thuật này không thay thế đánh giá nghiệp vụ độc lập.

Kích hoạt được kiểm toán; worker kiểm tra checksum trước nạp. Mô hình HOG cũ không được kích hoạt trong pipeline mới. Bản ghi lịch sử có thể giữ để truy vết, không có nghĩa còn chạy thuật toán cũ.

## 5. Điều kiện cho mô hình chuyên biệt tốt hơn

Dành test set khóa độc lập theo công tơ trước fine-tune. Đo riêng định vị, đọc crop và end-to-end; exact-match/CER/coverage, lỗi khi có câu trả lời, P50/P95, RAM và từng nhóm ảnh. Đánh giá ảnh chuyển số và phản chiếu, không chỉ ảnh rõ.

Fine-tune deep reader hoặc thay Ridge bằng detector/keypoint model là bước phát triển **chưa có nút hoàn tất tự động** trong bản này. Cần thêm chương trình train/export/import, tài nguyên GPU phù hợp, kiểm thử tương thích và xem giấy phép phụ thuộc. Không hứa chỉ thêm data là AI đã đạt độ chính xác sản xuất.

Xem [pipeline](ai-pipeline.md), [độ tin cậy](ai-reliability.md), [báo cáo chẩn đoán](reports/ai-diagnostic-2026-10-12.md).
