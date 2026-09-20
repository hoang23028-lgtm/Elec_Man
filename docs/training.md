# Dữ liệu huấn luyện

Nhãn huấn luyện được tạo từ kết quả đã được con người xác nhận và lưu trong PostgreSQL. Không commit ảnh hoặc tệp nhãn chứa mã khách hàng vào source code vì ảnh đồng hồ có thể chứa dữ liệu cá nhân hoặc vận hành. Ảnh nguồn nằm trong volume lưu trữ được bảo vệ và chỉ người dùng đã xác thực mới truy cập được.

Trước khi kích hoạt mô hình nhận dạng thực tế, hãy thu thập tập dữ liệu được chia tách với nhiều loại đồng hồ, ánh sáng, độ mờ, góc chụp, bụi bẩn/che khuất và tổ hợp chữ số đại diện. Giữ riêng tập kiểm thử độc lập và công bố chỉ số chính xác/lỗi cho mã khách hàng và chỉ số điện.

`meter-ocr-baseline-v2-integer` đang triển khai là bộ OCR dựng sẵn, không phải mô hình được huấn luyện bằng ảnh mẫu. Nó cho phép người vận hành tải ảnh ngay, sửa kết quả OCR và tạo nhãn đáng tin cậy. Không mô tả một lần đọc đúng ảnh mẫu là độ chính xác huấn luyện.

Các xác nhận thủ công do ứng dụng ghi lại là nguồn nhãn huấn luyện. Trainer chỉ chọn bản ghi `CONFIRMED` có `reviewed_by`, mã khách hàng và số điện nguyên đầy đủ; kết quả tự động xác nhận không đi thẳng vào dataset.

Trainer chạy trong container độc lập. Mặc định, khi có ít nhất 20 mẫu đã kiểm duyệt và thêm tối thiểu 10 mẫu kể từ lần thành công gần nhất, hệ thống tự tạo phiên huấn luyện. Dataset được sắp xếp và chia train/validation ổn định theo SHA-256 để hạn chế rò rỉ giữa các tập. Có thể theo dõi hoặc tạo phiên thủ công tại trang **Vòng đời mô hình**.

Phiên bản đầu huấn luyện bộ phân loại chữ số nearest-centroid trên vùng bánh số nguyên, lưu artifact `.npz` không sử dụng pickle, tính checksum SHA-256 và đăng ký model ở trạng thái `TESTING`. Quản trị viên phải xem chỉ số validation và độ phủ chữ số trước khi kích hoạt. Worker kiểm tra checksum và tự nạp model `ACTIVE` cho tác vụ tiếp theo; RapidOCR/Tesseract vẫn là phương án cơ sở.

Ngưỡng 20 mẫu chỉ giúp chạy thử pipeline, không chứng minh chất lượng sản xuất. Cần hàng trăm đến hàng nghìn ảnh đa dạng, đủ chữ số 0–9 và tập kiểm thử độc lập trước khi tin cậy tự động xác nhận.
