# Bảo mật và xác thực

Hệ thống sử dụng các tài khoản quản trị viên, mật khẩu băm Argon2id, phiên làm việc không trong suốt phía máy chủ và cookie HttpOnly. Cơ sở dữ liệu chỉ lưu giá trị băm SHA-256 của phiên và token CSRF. Cookie có thuộc tính `Secure` trong production và dùng `SameSite=Strict`.

Mọi endpoint thay đổi trạng thái có xác thực đều yêu cầu `X-CSRF-Token` được trả về khi đăng nhập. Frontend chỉ giữ token CSRF không phải thông tin đăng nhập này trong bộ nhớ, không lưu vào localStorage. Đăng nhập được giới hạn đồng thời theo IP và tổ hợp IP/tên đăng nhập trong cửa sổ 15 phút. Bộ giới hạn đặt trần số khóa theo dõi để tránh làm cạn bộ nhớ bằng username giả, phù hợp với phạm vi một máy chủ.

Tạo quản trị viên sau khi áp dụng migration:

```powershell
docker compose exec -e "ADMIN_INITIAL_PASSWORD=<mat-khau-tam>" backend python -m app.scripts.init_admin --username admin_operator
```

Không ghi mật khẩu thật trực tiếp vào lịch sử terminal; dùng quy trình nhập bảo mật trong [installation.md](installation.md). Sau khi có tài khoản đầu tiên, tạo các tài khoản khác trong trang Quản trị. Đổi mật khẩu hoặc khóa/xóa tài khoản sẽ thu hồi các phiên liên quan.

Trong production, đặt `SESSION_SECRET` thành giá trị ngẫu nhiên duy nhất dài ít nhất 32 ký tự, thay mật khẩu PostgreSQL mẫu và khai báo chính xác `ALLOWED_HOSTS`. Quá trình khởi động sẽ từ chối secret/mật khẩu mẫu và host ký tự đại diện trong production. Tài liệu API tự động cũng bị tắt trong môi trường này. Không bao giờ commit tệp `.env`.

Nginx mặc định chỉ công bố cổng HTTP trên `127.0.0.1`. Chỉ đặt `NGINX_BIND_ADDRESS=0.0.0.0` khi dịch vụ nằm sau reverse proxy HTTPS đáng tin cậy hoặc tường lửa đã được cấu hình. API từ chối Host ngoài danh sách, không cho trình duyệt cache phản hồi và các tệp ảnh/JSON/Excel yêu cầu phiên quản trị hợp lệ.

Các container ứng dụng chạy bằng người dùng không đặc quyền, loại bỏ toàn bộ Linux capabilities, bật `no-new-privileges` và dùng filesystem gốc chỉ đọc ở các tiến trình Python. Thư mục tạm được cấp bằng `tmpfs`; chỉ volume dữ liệu hoặc mô hình đúng vai trò mới có quyền ghi. Log ứng dụng được phát ra stdout để Docker quản lý thay vì gắn một volume log không được sử dụng.

Image nền được ghim theo digest để bản dựng có thể tái lập và tránh tag bị thay thế ngoài ý muốn. Cần định kỳ cập nhật digest sau khi kiểm tra release bảo mật chính thức; PostgreSQL giữ cùng major version khi cập nhật minor để volume dữ liệu tương thích.

Dashboard là trang chỉ đọc công khai theo yêu cầu sản phẩm hiện tại và có thể hiển thị mã khách hàng cùng dữ liệu tiền điện. Trước khi công bố hệ thống ra Internet, cần quyết định rõ dữ liệu này có được phép công khai hay phải ẩn mã khách hàng/yêu cầu đăng nhập. Tệp sao lưu chứa dữ liệu nghiệp vụ và hiện không tự mã hóa; lưu chúng trong vùng được mã hóa, giới hạn quyền truy cập và quản lý khóa tách biệt.
