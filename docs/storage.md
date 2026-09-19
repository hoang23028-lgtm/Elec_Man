# Lưu trữ và tải ảnh

Ảnh được lưu bằng tên UUID do máy chủ tạo bên dưới `STORAGE_ROOT`; tên tệp gốc chỉ là metadata. Volume lưu trữ không được phục vụ trực tiếp qua web. Việc xem trước luôn đi qua endpoint API đã xác thực.

Mỗi lần tải lên là một yêu cầu HTTP được kiểm soát. Backend kiểm tra phần mở rộng, MIME do trình duyệt cung cấp, chữ ký tệp, khả năng giải mã an toàn bằng Pillow, định dạng sau giải mã, kích thước, số điểm ảnh và dung lượng đã cấu hình. Hệ thống tính SHA-256 trong lúc truyền xuống đĩa và từ chối ảnh trùng hoàn toàn trong cùng lô. Ảnh thu nhỏ được tạo riêng; ảnh gốc không bao giờ bị chỉnh sửa.
