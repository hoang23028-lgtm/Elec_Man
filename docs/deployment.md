# Nền tảng triển khai

Sao chép `.env.example` thành `.env`; đặt mật khẩu PostgreSQL mạnh và cập nhật mật khẩu trong `DATABASE_URL` cho khớp. Khai báo `ALLOWED_HOSTS` bằng các tên miền thực tế. Khởi động bằng `docker compose up --build`. Xác nhận các endpoint kiểm tra hoạt động và sẵn sàng thông qua Nginx.

Mặc định Nginx chỉ bind vào `127.0.0.1`. Trong production, chỉ đổi `NGINX_BIND_ADDRESS` sau khi đã đặt reverse proxy/tường lửa; kết thúc HTTPS bằng chứng chỉ đáng tin cậy và chỉ cấu hình HSTS sau khi mọi truy cập đã dùng HTTPS. Không công khai cổng PostgreSQL. Các volume lâu dài giữ dữ liệu cơ sở dữ liệu, vùng lưu trữ, mô hình và nhật ký.

## Điều kiện bắt buộc trước khi go-live

- Dùng `.env` riêng trên máy chủ, không commit; thay toàn bộ giá trị mẫu của PostgreSQL và `SESSION_SECRET`.
- Đặt `APP_ENV=production`, `ENFORCE_HTTPS=true`, `FRONTEND_ORIGIN=https://<tên-miền>` và `ALLOWED_HOSTS=<tên-miền>`; cài chứng thư TLS hợp lệ trước khi bật HSTS.
- Chỉ công bố cổng 443 qua tường lửa/reverse proxy. Không publish backend, worker, trainer hoặc PostgreSQL.
- Quyết định chính thức việc dashboard công khai có được phép hiển thị mã khách hàng và dữ liệu tiền điện hay không. Nếu không, phải yêu cầu đăng nhập hoặc ẩn dữ liệu trước khi mở Internet.
- Chạy toàn bộ test, quét dependency và secret; xác nhận frontend/nginx không phân giải được hostname `postgres` còn backend vẫn kết nối được.
- Đặt lịch backup hằng ngày, mã hóa và chuyển ít nhất một bản ra ngoài máy chủ; diễn tập restore trên môi trường tách biệt.
- Thu thập log JSON tập trung, cảnh báo theo healthcheck, HTTP 5xx, `LOGIN_FAILED`, job thất bại và dung lượng đĩa. Không dùng `LOG_LEVEL=DEBUG` ở production.
- Sau triển khai, kiểm tra cookie có `HttpOnly`, `Secure`, `SameSite=Strict`, CORS chỉ trả về origin chính thức và các security header còn nguyên qua reverse proxy.
