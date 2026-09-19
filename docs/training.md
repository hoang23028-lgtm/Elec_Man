# Dữ liệu huấn luyện

`training/annotations.jsonl` là tệp nhãn có quản lý phiên bản dành cho các mẫu huấn luyện đã phê duyệt. Ảnh không được commit vì ảnh đồng hồ có thể chứa dữ liệu cá nhân hoặc vận hành và phải nằm trong vùng lưu trữ được bảo vệ.

Mỗi dòng yêu cầu checksum SHA-256, mã khách hàng đã xác minh và toàn bộ chỉ số điện. Bản ghi mẫu hiện đại diện cho `ảnh.jpg` với `KH003` và `05068.4 kWh`; bánh số cuối màu đỏ là chữ số hàng phần mười.

Một ảnh chỉ là mẫu gán nhãn ban đầu và dữ liệu kiểm thử thủ công, không phải tập huấn luyện đủ lớn. Trước khi kích hoạt mô hình nhận dạng thực tế, hãy thu thập tập dữ liệu được chia tách với nhiều loại đồng hồ, ánh sáng, độ mờ, góc chụp, bụi bẩn/che khuất và tổ hợp chữ số đại diện. Giữ riêng tập kiểm thử độc lập và công bố chỉ số chính xác/lỗi cho mã khách hàng và chỉ số điện.

`meter-ocr-baseline-v1` đang triển khai là bộ OCR dựng sẵn, không phải mô hình được huấn luyện bằng ảnh mẫu. Nó cho phép người vận hành tải ảnh ngay, sửa kết quả OCR và tạo nhãn đáng tin cậy. Không mô tả một lần đọc đúng ảnh mẫu là độ chính xác huấn luyện.

Các xác nhận thủ công do ứng dụng ghi lại là nguồn nhãn vận hành trong tương lai. Chỉ huấn luyện từ nhãn đã được người có thẩm quyền kiểm duyệt, đồng thời lưu phiên bản mô hình và báo cáo đánh giá cùng mọi gói mô hình triển khai.
