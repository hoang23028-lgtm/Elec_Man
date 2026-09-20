# Nền tảng triển khai

Sao chép `.env.example` thành `.env`; đặt mật khẩu PostgreSQL mạnh và cập nhật mật khẩu trong `DATABASE_URL` cho khớp. Khai báo `ALLOWED_HOSTS` bằng các tên miền thực tế. Khởi động bằng `docker compose up --build`. Xác nhận các endpoint kiểm tra hoạt động và sẵn sàng thông qua Nginx.

Mặc định Nginx chỉ bind vào `127.0.0.1`. Trong production, chỉ đổi `NGINX_BIND_ADDRESS` sau khi đã đặt reverse proxy/tường lửa; kết thúc HTTPS bằng chứng chỉ đáng tin cậy và chỉ cấu hình HSTS sau khi mọi truy cập đã dùng HTTPS. Không công khai cổng PostgreSQL. Các volume lâu dài giữ dữ liệu cơ sở dữ liệu, vùng lưu trữ, mô hình và nhật ký.
