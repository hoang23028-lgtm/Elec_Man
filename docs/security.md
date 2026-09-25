# Bảo mật và xác thực

Hệ thống sử dụng các tài khoản quản trị viên, mật khẩu băm Argon2id, phiên làm việc không trong suốt phía máy chủ và cookie HttpOnly. Cơ sở dữ liệu chỉ lưu HMAC-SHA-256 của phiên và token CSRF bằng khóa `SESSION_SECRET`; thay khóa này sẽ thu hồi toàn bộ phiên hiện có. Cookie có thuộc tính `Secure` trong production và dùng `SameSite=Strict`.

Mọi endpoint thay đổi trạng thái có xác thực đều yêu cầu `X-CSRF-Token` được trả về khi đăng nhập. Frontend chỉ giữ token CSRF không phải thông tin đăng nhập này trong bộ nhớ, không lưu vào localStorage. Đăng nhập được giới hạn đồng thời theo IP và tổ hợp IP/tên đăng nhập trong cửa sổ 15 phút. Bộ giới hạn đặt trần số khóa theo dõi để tránh làm cạn bộ nhớ bằng username giả, phù hợp với phạm vi một máy chủ.

Endpoint đăng ký công khai chỉ tạo tài khoản `is_active=false`; tài khoản không thể đăng nhập hoặc truy cập chức năng nghiệp vụ trước khi một quản trị viên hiện hữu kích hoạt tại trang Quản trị. Mỗi IP được gửi tối đa năm yêu cầu trong một giờ. Phản hồi đăng ký luôn giống nhau dù tên đăng nhập đã tồn tại, nhằm hạn chế dò danh sách tài khoản. Mật khẩu đăng ký được băm Argon2id ngay trên backend và không xuất hiện trong log hoặc audit.

Tạo quản trị viên sau khi áp dụng migration:

```powershell
docker compose exec -e "ADMIN_INITIAL_PASSWORD=<mat-khau-tam>" backend python -m app.scripts.init_admin --username admin_operator
```

Không ghi mật khẩu thật trực tiếp vào lịch sử terminal; dùng quy trình nhập bảo mật trong [installation.md](installation.md). Sau khi có tài khoản đầu tiên, tạo các tài khoản khác trong trang Quản trị. Đổi mật khẩu hoặc khóa/xóa tài khoản sẽ thu hồi các phiên liên quan.

Trong production, đặt `SESSION_SECRET` thành giá trị ngẫu nhiên duy nhất dài ít nhất 32 ký tự, thay mật khẩu PostgreSQL mẫu và khai báo chính xác `ALLOWED_HOSTS`. Quá trình khởi động sẽ từ chối secret/mật khẩu mẫu, host ký tự đại diện, HTTP chưa được cưỡng chế và `FRONTEND_ORIGIN` không dùng HTTPS trong production. Tài liệu API tự động cũng bị tắt trong môi trường này. Không bao giờ commit tệp `.env`.

Nginx mặc định chỉ công bố cổng HTTP trên `127.0.0.1`. Chỉ đặt `NGINX_BIND_ADDRESS=0.0.0.0` khi dịch vụ nằm sau reverse proxy HTTPS đáng tin cậy hoặc tường lửa đã được cấu hình. API từ chối Host ngoài danh sách, không cho trình duyệt cache phản hồi và các tệp ảnh/JSON/Excel yêu cầu phiên quản trị hợp lệ.

API gắn mã `X-Request-ID`, trả thông báo chung cho lỗi ngoài dự kiến và chỉ ghi traceback ở log máy chủ. Không đưa chuỗi lỗi nội bộ, đường dẫn hoặc thông tin kết nối vào phản hồi người dùng. Header chống MIME sniffing, clickjacking, nhúng chéo và quyền camera/microphone/vị trí được đặt ở cả API và Nginx.

Khi triển khai tên miền, dùng cấu hình mẫu `docker/nginx.https.conf.example`, gắn chứng thư vào `/etc/nginx/tls`, công bố cổng 443, rồi đặt `APP_ENV=production`, `ENFORCE_HTTPS=true`, `FRONTEND_ORIGIN=https://<tên-miền>` và `ALLOWED_HOSTS=<tên-miền>`. Cấu hình mẫu chuyển hướng HTTP bằng 308 và chỉ bật HSTS ở máy chủ TLS. Không bật HSTS trước khi chứng thư và toàn bộ subdomain đã được kiểm tra.

Các container ứng dụng chạy bằng người dùng không đặc quyền, loại bỏ toàn bộ Linux capabilities, bật `no-new-privileges` và dùng filesystem gốc chỉ đọc ở các tiến trình Python. Thư mục tạm được cấp bằng `tmpfs`; chỉ volume dữ liệu hoặc mô hình đúng vai trò mới có quyền ghi. Log ứng dụng được phát ra stdout để Docker quản lý thay vì gắn một volume log không được sử dụng.

Docker xoay vòng log theo giới hạn 10 MB × 5 tệp cho mỗi container. Theo dõi `health/ready`, trạng thái healthcheck và các sự kiện JSON có mức `ERROR`; dùng `request_id`, `job_id` hoặc `run_id` để đối chiếu. Không hạ `LOG_LEVEL` xuống `DEBUG` trong production.

PostgreSQL chỉ tham gia mạng Docker `internal` và không ánh xạ cổng ra host. Mã ứng dụng dùng biểu thức SQLAlchemy có bind parameter; SQL tĩnh chỉ xuất hiện trong migration và healthcheck, không ghép dữ liệu người dùng vào câu lệnh.

Image nền được ghim theo digest để bản dựng có thể tái lập và tránh tag bị thay thế ngoài ý muốn. Cần định kỳ cập nhật digest sau khi kiểm tra release bảo mật chính thức; PostgreSQL giữ cùng major version khi cập nhật minor để volume dữ liệu tương thích.

Dashboard là trang chỉ đọc công khai theo yêu cầu sản phẩm hiện tại và có thể hiển thị mã khách hàng cùng dữ liệu tiền điện. Trước khi công bố hệ thống ra Internet, cần quyết định rõ dữ liệu này có được phép công khai hay phải ẩn mã khách hàng/yêu cầu đăng nhập. Tệp sao lưu chứa dữ liệu nghiệp vụ và hiện không tự mã hóa; lưu chúng trong vùng được mã hóa, giới hạn quyền truy cập và quản lý khóa tách biệt.
