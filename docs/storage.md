# Lưu trữ và tải ảnh

Ảnh được lưu bằng tên UUID do máy chủ tạo bên dưới `STORAGE_ROOT`; tên tệp gốc chỉ là metadata. Volume lưu trữ không được phục vụ trực tiếp qua web. Việc xem trước luôn đi qua endpoint API đã xác thực.

Mỗi lần tải lên là một yêu cầu HTTP được kiểm soát. Backend kiểm tra phần mở rộng, MIME do trình duyệt cung cấp, chữ ký tệp, khả năng giải mã an toàn bằng Pillow, định dạng sau giải mã, kích thước, số điểm ảnh và dung lượng đã cấu hình. Hệ thống tính SHA-256 trong lúc truyền xuống đĩa và từ chối ảnh trùng hoàn toàn trong cùng lô. Ảnh thu nhỏ được tạo riêng; ảnh gốc không bao giờ bị chỉnh sửa.

## Ảnh sau kiểm tra

Khi kết quả được xác nhận thủ công hoặc tự động, hệ thống sao chép ảnh gốc vào `STORAGE_ROOT/reviewed/DD-MM-YYYY/` theo ngày xác nhận tại Việt Nam. Tệp được đổi tên theo mã khách hàng, ví dụ `PN2.001.jpg`. Nếu cùng một khách hàng có nhiều ảnh được xác nhận trong ngày, hệ thống dùng `PN2.001_2.jpg`, `PN2.001_3.jpg`, ... để không ghi đè dữ liệu. Khi quản trị viên sửa mã khách hàng của kết quả đã xác nhận, bản lưu cũng được đổi sang mã mới. Đường dẫn của bản lưu được ghi trong bảng `images` và nhật ký kiểm toán.

Ảnh bị từ chối không được đưa vào thư mục này vì chưa có mã khách hàng cuối cùng hợp lệ. Ảnh gốc UUID vẫn được giữ nguyên để xem lại, truy vết và huấn luyện. Trong Docker, thư mục nằm trong volume `storage_data`; khi chạy trực tiếp, vị trí mặc định là `storage/reviewed`.

## Dữ liệu xác nhận trong PostgreSQL

Bảng `confirmed_monthly_readings` là nguồn dữ liệu nghiệp vụ chính thức. Bản ghi chỉ được tạo sau khi kết quả được xác nhận thủ công hoặc tự động và mã khách hàng đã đối chiếu thành công với bảng `customers`. Mỗi khách hàng có tối đa một bản ghi trong một tháng; lần xác nhận mới của cùng kỳ sẽ cập nhật chỉ số và ảnh chính thức, đồng thời lưu thông tin trước/sau trong audit log.

Mỗi bản ghi chứa khóa ngoại khách hàng, mã khách hàng chuẩn, tháng ghi điện, chỉ số nguyên, thời điểm/người xác nhận, tên và MIME ảnh, SHA-256 và toàn bộ nội dung ảnh dạng `BYTEA`. Dashboard và báo cáo tháng chỉ đọc bảng này. Ảnh hoặc kết quả đang chờ duyệt không được ghi vào bảng dữ liệu chính thức. Khi kết quả chính thức bị từ chối, bản ghi tháng chỉ bị xóa nếu nó vẫn đang tham chiếu chính ảnh đó.
