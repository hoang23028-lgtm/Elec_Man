# Dữ liệu huấn luyện

Nhãn huấn luyện được tạo từ kết quả đã được con người xác nhận và lưu trong PostgreSQL. Không commit ảnh hoặc tệp nhãn chứa mã khách hàng vào source code vì ảnh đồng hồ có thể chứa dữ liệu cá nhân hoặc vận hành. Ảnh nguồn nằm trong volume lưu trữ được bảo vệ và chỉ người dùng đã xác thực mới truy cập được.

Trước khi kích hoạt mô hình nhận dạng thực tế, hãy thu thập tập dữ liệu được chia tách với nhiều loại đồng hồ, ánh sáng, độ mờ, góc chụp, bụi bẩn/che khuất và tổ hợp chữ số đại diện. Giữ riêng tập kiểm thử độc lập và công bố chỉ số chính xác/lỗi cho mã khách hàng và chỉ số điện.

`meter-ocr-baseline-v2-integer` đang triển khai là bộ OCR dựng sẵn, không phải mô hình được huấn luyện bằng ảnh mẫu. Nó cho phép người vận hành tải ảnh ngay, sửa kết quả OCR và tạo nhãn đáng tin cậy. Không mô tả một lần đọc đúng ảnh mẫu là độ chính xác huấn luyện.

Các xác nhận thủ công do ứng dụng ghi lại là nguồn nhãn huấn luyện. Trainer chỉ chọn bản ghi `CONFIRMED` có `reviewed_by`, mã khách hàng, số điện nguyên và **vùng chỉ số đã được con người khoanh**; kết quả tự động xác nhận hoặc ảnh chưa khoanh vùng không đi thẳng vào dataset.

Trainer chạy trong container độc lập. Mặc định, khi có ít nhất 20 mẫu đã kiểm duyệt và thêm tối thiểu 10 mẫu kể từ lần thành công gần nhất, hệ thống tự tạo phiên huấn luyện. Dataset được sắp xếp và chia train/validation ổn định theo SHA-256 để hạn chế rò rỉ giữa các tập. Có thể theo dõi hoặc tạo phiên thủ công tại trang **Vòng đời mô hình**.

Pipeline chuyên biệt cắt vùng bánh số nguyên theo khung tọa độ đã xác nhận, tăng cường từng ảnh bằng dịch chuyển ngang và thay đổi tương phản, sau đó trích xuất đặc trưng HOG. Bộ phân loại softmax được huấn luyện với chuẩn hóa đặc trưng và trọng số cân bằng lớp để hạn chế thiên lệch về những chữ số xuất hiện nhiều. Artifact `.npz` chỉ chứa mảng số, không sử dụng pickle; hệ thống tính checksum SHA-256 và đăng ký model ở trạng thái `TESTING`.

Quản trị viên phải xem độ chính xác validation và độ phủ chữ số trước khi kích hoạt. Model chỉ được kích hoạt khi tập huấn luyện phủ đủ chữ số `0–9` và độ chính xác chữ số trên validation đạt ít nhất 90%. Worker xác minh checksum rồi tự nạp model `ACTIVE` cho tác vụ tiếp theo; artifact nearest-centroid cũ vẫn được hỗ trợ để không làm gián đoạn bản triển khai, còn RapidOCR/Tesseract tiếp tục là phương án cơ sở.

Quy trình sử dụng trên giao diện là: **Vận hành → tải ảnh → xử lý OCR → mở ảnh → khoanh đúng dãy bánh số màu đen (không lấy bánh đỏ sau dấu phẩy) → sửa mã khách hàng/số điện → xác nhận → Vòng đời mô hình → Huấn luyện ngay → xem đánh giá → Kích hoạt**. Có thể kéo chuột/cảm ứng, điều chỉnh độc lập bằng bốn tay nắm ở các góc hoặc nhập bốn tọa độ phần trăm bằng bàn phím. Khi một tay nắm được chọn, dùng phím mũi tên để tinh chỉnh và giữ `Shift` để di chuyển nhanh hơn. Chỉ tải ảnh chưa tạo ra nhãn đáng tin cậy; vùng chỉ số và kết quả phải được con người xác nhận trước khi ảnh được đưa vào dataset. Mọi lần thay đổi vùng đều được ghi nhật ký với giá trị trước và sau.

Trong cửa sổ khoanh vùng, khung xanh là vùng hệ thống tự phát hiện và khung đỏ là vùng do người dùng xác định. Nút **Xác định chỉ số** gửi vùng đỏ tới worker OCR và cập nhật số điện đề xuất, nhưng luôn giữ ảnh trong danh sách **Cần xử lý** cho đến khi người dùng bấm **Xác nhận**.

Ngưỡng 20 mẫu chỉ giúp chạy thử pipeline, không chứng minh chất lượng sản xuất. Cần hàng trăm đến hàng nghìn ảnh đa dạng, đủ chữ số 0–9 và tập kiểm thử độc lập trước khi tin cậy tự động xác nhận.
