# Quản trị

Cấu hình hệ thống, vòng đời mô hình, chỉ số đánh giá và lịch sử kiểm toán là các chức năng dành cho quản trị viên đã xác thực.

Thay đổi cấu hình được kiểm tra, lưu trong PostgreSQL và ghi nhật ký kiểm toán. Các giá trị điều khiển lúc khởi động vẫn là chính sách triển khai và chỉ có hiệu lực sau khi cập nhật cấu hình môi trường rồi khởi động lại dịch vụ liên quan; hệ thống không tự động khởi động lại ngầm.

Đăng ký mô hình chỉ chấp nhận tệp đã có bên dưới `MODELS_ROOT`. API phân giải đường dẫn trong thư mục gốc này và xác minh SHA-256 được gửi lên. Bản ghi mới bắt đầu ở trạng thái `TESTING`. Khi kích hoạt, hệ thống lưu trữ mô hình đang hoạt động trước đó cùng loại và ghi sự kiện kiểm toán, nhưng chủ động không nạp nóng mã tùy ý hoặc tự động triển khai mô hình.

Đánh giá sử dụng dự đoán AI bất biến ghép với giá trị cuối cùng đã được con người xác nhận. Độ chính xác tuyệt đối của mã khách hàng, chỉ số điện và từng chữ số chỉ được báo cáo trên các mẫu đã xác nhận. Các chỉ số vận hành này không thay thế tập kiểm thử độc lập. Chỉ số tự động chấp nhận sai chưa khả dụng vì OCR cơ sở vẫn yêu cầu kiểm duyệt mọi kết quả.
