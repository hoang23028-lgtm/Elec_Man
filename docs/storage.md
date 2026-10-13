# Lưu trữ và tải ảnh

Ảnh được lưu bằng tên UUID do máy chủ tạo bên dưới `STORAGE_ROOT`; tên tệp gốc chỉ là metadata. Volume lưu trữ không được phục vụ trực tiếp qua web. Việc xem trước luôn đi qua endpoint API đã xác thực.

Mỗi lần tải lên là một yêu cầu HTTP được kiểm soát. Backend kiểm tra phần mở rộng, MIME do trình duyệt cung cấp, chữ ký tệp, khả năng giải mã an toàn bằng Pillow, định dạng sau giải mã, kích thước, số điểm ảnh và dung lượng đã cấu hình. Hệ thống tính SHA-256 trong lúc truyền xuống đĩa và từ chối ảnh trùng hoàn toàn trong cùng lô. Ảnh thu nhỏ được tạo riêng; ảnh gốc không bao giờ bị chỉnh sửa.

## Ảnh sau kiểm tra

Khi kết quả được xác nhận thủ công, hệ thống sao chép ảnh gốc vào `STORAGE_ROOT/reviewed/DD-MM-YYYY/` theo ngày xác nhận tại Việt Nam. Tên tệp dùng mã khách hàng chuẩn trong database, ví dụ `PN2.001.jpg`; khi trùng tên sẽ thêm `_2`, `_3`, ... để không ghi đè. Đường dẫn được ghi trong bảng `images` và nhật ký kiểm toán.

Khi đổi mã hoặc từ chối, bản sao cũ chỉ bị xóa sau khi transaction database commit thành công. Rollback/đóng session sẽ dọn bản sao mới chưa được lưu. Ảnh gốc luôn giữ nguyên. Nếu tiến trình bị tắt đột ngột hoặc không thể xóa file, có thể còn bản sao dư cần đối soát; không tự quét xóa ảnh không rõ nguồn gốc.

Ảnh bị từ chối không được đưa vào thư mục này vì chưa có mã khách hàng cuối cùng hợp lệ. Ảnh gốc UUID vẫn được giữ nguyên để xem lại, truy vết và huấn luyện. Trong Docker, thư mục nằm trong volume `storage_data`; khi chạy trực tiếp, vị trí mặc định là `storage/reviewed`.

## Dữ liệu xác nhận trong PostgreSQL

Bảng `confirmed_monthly_readings` là nguồn dữ liệu nghiệp vụ chính thức. Chỉ tạo sau xác nhận thủ công và đối chiếu khách hàng thành công. Mỗi khách hàng có tối đa một bản ghi mỗi tháng. Chỉ được chỉnh sửa bản ghi cùng ảnh; xác nhận một ảnh khác trùng kỳ trả về HTTP 409, không ghi đè ảnh cũ.

Mỗi bản ghi chứa khóa ngoại khách hàng, mã khách hàng chuẩn, tháng ghi điện, chỉ số nguyên, thời điểm/người xác nhận, tên và MIME ảnh, SHA-256 và toàn bộ nội dung ảnh dạng `BYTEA`. Dashboard và báo cáo tháng chỉ đọc bảng này. Ảnh hoặc kết quả đang chờ duyệt không được ghi vào bảng dữ liệu chính thức. Khi kết quả chính thức bị từ chối, bản ghi tháng chỉ bị xóa nếu nó vẫn đang tham chiếu chính ảnh đó.

Migration `20261003_0026` thêm bản chụp chỉ số khởi tạo và mục đích sử dụng lúc xác nhận. Sửa hồ sơ khách hàng không đổi các đầu vào tính tiền của kỳ cũ. Dữ liệu đã có trước migration chỉ có thể bổ sung từ hồ sơ khách hàng hiện tại, không khôi phục được thông tin lịch sử chưa từng lưu. Đây chưa phải ảnh chụp toàn bộ hóa đơn hoặc phiên bản biểu giá.

Dashboard không tính chênh lệch thành một tháng khi thiếu kỳ liền trước. Các tổng và xu hướng được gom ở database, chỉ tính chi tiết cho trang đang xem. Xuất báo cáo không tải cột ảnh BYTEA vào bộ nhớ.
