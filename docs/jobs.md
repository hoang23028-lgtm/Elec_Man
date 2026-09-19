# Tác vụ xử lý

Hệ thống sử dụng PostgreSQL làm hàng đợi. Tiến trình xử lý nhận một tác vụ đủ điều kiện trong giao dịch bằng `FOR UPDATE SKIP LOCKED`, nhờ đó có thể thêm tiến trình thứ hai mà không nhận trùng tác vụ. Tác vụ `PROCESSING` bị gián đoạn được khôi phục sau thời hạn đã cấu hình; lỗi được thử lại theo thời gian chờ tăng dần cho đến khi đạt `MAX_RETRY_COUNT`.

Bộ xử lý hiện tại là `OCR_BASELINE`. Nó ghi lại chất lượng, OCR, vùng phát hiện, độ tin cậy và phiên bản mô hình, đồng thời đưa mọi đầu ra vào kiểm duyệt thủ công. Đây là bộ khởi đầu dựng sẵn để thu thập nhãn đã xác minh, không phải mô hình đồng hồ điện sản xuất đã huấn luyện.

Dịch vụ Compose `migrate` áp dụng toàn bộ migration Alembic trước khi backend và tiến trình xử lý khởi động, giúp loại bỏ xung đột khởi tạo bảng hàng đợi.
