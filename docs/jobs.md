# Tác vụ xử lý

Hệ thống sử dụng PostgreSQL làm hàng đợi. Tiến trình xử lý nhận một tác vụ đủ điều kiện trong giao dịch bằng `FOR UPDATE SKIP LOCKED`, nhờ đó có thể thêm tiến trình thứ hai mà không nhận trùng tác vụ. Tác vụ `PROCESSING` bị gián đoạn được khôi phục sau thời hạn đã cấu hình; lỗi được thử lại theo thời gian chờ tăng dần cho đến khi đạt `MAX_RETRY_COUNT`.

Bộ xử lý hiện tại ghi lại chất lượng, OCR, vùng phát hiện, độ tin cậy và phiên bản mô hình. Tất cả đầu ra được đưa vào hàng chờ kiểm duyệt cho đến khi có tập kiểm thử độc lập đủ lớn và chính sách tự động xác nhận được phê duyệt. Đây là pipeline thu thập nhãn và đánh giá có kiểm soát; điểm tin cậy OCR chưa phải xác suất đã hiệu chuẩn.

Dịch vụ Compose `migrate` áp dụng toàn bộ migration Alembic trước khi backend và tiến trình xử lý khởi động, giúp loại bỏ xung đột khởi tạo bảng hàng đợi.

## Theo dõi và xử lý lỗi

WORKER_POLL_INTERVAL_SECONDS, MAX_RETRY_COUNT và JOB_STUCK_TIMEOUT_SECONDS được Compose truyền vào worker. Theo dõi trạng thái job, retry và thời điểm lỗi; khi hết retry, kiểm tra reader/file/nguồn dữ liệu trước chạy lại. Không bật lại hàng loạt để che lỗi cố định. Worker COMPLETED chỉ là đã xử lý đề xuất, không phải kiểm duyệt/xác nhận.

Trainer có hàng đợi và cơ chế lỗi riêng, không dùng MAX_RETRY_COUNT của job OCR để tự lặp huấn luyện. Xem [huấn luyện](training.md).
