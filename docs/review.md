# Quy trình kiểm duyệt

Trang Vận hành gồm danh sách ảnh, vùng xem/khoanh ảnh và bảng nhập chỉ số. Các bộ lọc: Cần xử lý (Chưa gắn nhãn + Đã gắn nhãn), Đã xác nhận và Đã từ chối. Hiện mọi kết quả đều cần con người xác nhận; độ tin cậy trên 90% không tự tạo dữ liệu chính thức.

Người kiểm duyệt ghi giá trị cuối cùng vào `meter_readings`; mỗi trường bị thay đổi tạo một bản ghi `manual_corrections`. Mọi thao tác xác nhận, từ chối và sửa dữ liệu đã xác nhận đều được kiểm toán. Giá trị đã sửa không bao giờ ghi đè giá trị AI.

## Lưu nhãn và xác nhận

- Chọn **Vùng công tơ → Lưu vùng công tơ** để lưu riêng bốn góc, không cần chỉ số hay mã khách hàng.
- Chọn **Vùng chỉ số → Lưu nhãn chỉ số** để lưu vùng và chuỗi số nguyên 4–8 chữ số (giữ số 0 đầu, bỏ ô đỏ). Nhãn chuyển sang LABELED, chưa tạo chỉ số tháng chính thức.
- **Lưu và ảnh tiếp** chỉ chuyển khi ảnh không còn thay đổi chưa lưu. Nút lưu thông thường giữ ảnh hiện tại để kiểm tra.
- Xác nhận chính thức yêu cầu mã khách hàng tồn tại, chỉ số và kỳ tháng cụ thể. Một khách hàng chỉ có một ảnh chính thức mỗi tháng; ảnh khác cùng kỳ bị từ chối thay vì ghi đè.
- Có thể sửa dữ liệu đã xác nhận, hoặc từ chối lại với cảnh báo gỡ chỉ số khỏi dữ liệu tháng. Nhãn và ảnh gốc vẫn giữ lại.
- **Khôi phục về Cần xử lý** chỉ áp dụng ảnh đã từ chối. Nhãn thủ công hợp lệ được giữ ở LABELED; ảnh chưa có nhãn về PENDING. Sự kiện `REOPEN_RESULT` ghi người thao tác, thời gian và trạng thái trước/sau.

Danh sách tự cập nhật khi không chỉnh sửa; tạm dừng khi có bản nháp, vùng đang vẽ dở hoặc ảnh vừa lưu. Bộ đếm vẫn cập nhật. Bản nháp chỉ ở bộ nhớ trang, không thay thế việc bấm lưu; đóng trình duyệt có thể mất bản nháp. OCR chạy nền không tự ghi đè chỉ số người dùng đang nhập.

## Chống ghi đè và xác nhận thao tác

Mỗi bản ghi có revision. API thao tác nhãn/review nhận expected_revision; nếu người khác/phiên khác đã sửa, trả 412 thay vì ghi đè. Đọc lại kết quả trước khi lưu lại, không tự gửi revision mới cùng bản nháp cũ để vượt xung đột. Xung đột dữ liệu tháng 409 là quy tắc nghiệp vụ riêng.

Hộp thoại từ chối/chạy lại yêu cầu quyết định rõ; Hủy/Escape không chấp thuận thao tác. Trạng thái đang lưu chặn gửi trùng. Cập nhật dashboard/báo cáo trong cùng tab không sửa tệp người dùng đã tải xuống.
