# Cấu hình triển khai

`.env.example` là mẫu công khai, **không chứa secret dùng thật**. Bộ khởi động tạo `.env` riêng; giữ file ở máy triển khai/kho secret. Không sao chép cấu hình và dữ liệu thật vào repo.

## Giá trị và phạm vi hiệu lực

| Biến | Mặc định cài local | Ý nghĩa |
|---|---|---|
| APP_ENV | development | production bắt buộc cấu hình HTTPS và secret an toàn; test chỉ dùng môi trường kiểm thử |
| FRONTEND_ORIGIN | http://localhost | Origin chính xác của trình duyệt, không có dấu / cuối; bao gồm cổng nếu khác 80/443 |
| NGINX_BIND_ADDRESS | 127.0.0.1 | Chỉ nghe loopback; không tự công bố Internet |
| NGINX_HTTP_PORT | 80 | Cổng host của proxy HTTP local |
| ALLOWED_HOSTS | localhost,127.0.0.1 | Danh sách Host được API chấp nhận, không dùng * trong production |
| ENFORCE_HTTPS | false | Chỉ local dùng HTTP; production đặt true sau cấu hình TLS |
| POSTGRES_DB / POSTGRES_USER | electric_meter_ai / electric_meter_app | Database và role PostgreSQL |
| POSTGRES_PASSWORD | ngẫu nhiên khi cài | Phải khớp mật khẩu trong DATABASE_URL; không đổi chỉ file env trên volume đã khởi tạo |
| DATABASE_URL | PostgreSQL nội bộ | Driver psycopg, host postgres; không mở cổng database ra Internet |
| SESSION_SECRET | ngẫu nhiên khi cài | Ít nhất 32 ký tự; đổi khóa sẽ làm mọi phiên cũ mất hiệu lực |
| SESSION_COOKIE_NAME | ema_session | Tên cookie phiên |
| SESSION_TTL_HOURS | 8 | Thời hạn phiên: 1–168 giờ |
| MAX_IMAGE_SIZE_MB | 20 | Giới hạn mỗi ảnh ở backend, 1–100 MB |
| MAX_IMAGE_PIXELS | 40000000 | Giới hạn điểm ảnh sau giải mã; chống ảnh nén nhỏ nhưng giải nén lớn |
| WORKER_POLL_INTERVAL_SECONDS | 0.5 | Chu kỳ worker tìm công việc; phải >0 |
| MAX_RETRY_COUNT | 3 | Số lần thử công việc, 1–10 |
| JOB_STUCK_TIMEOUT_SECONDS | 900 | Thời hạn nhận diện công việc PROCESSING bị gián đoạn, tối thiểu 60 giây |
| PPOCR_READER_URL / PARSEQ_READER_URL | reader-ppocr / reader-parseq :8080 | Hai dịch vụ nội bộ; không trỏ tới endpoint không tin cậy |
| SEQUENCE_READER_TIMEOUT_SECONDS | 15 | Timeout gọi reader, 1–60 giây |
| METER_INTEGER_DIGITS_DEFAULT | 5 | Số bánh nguyên mặc định, 4–8; kiểm tra theo loại công tơ, không tính bánh đỏ |
| STORAGE_ROOT / MODELS_ROOT | /data/electric-meter-ai /models | Đường dẫn trong container, không phải thư mục trên Windows |
| DATABASE_POOL_SIZE / DATABASE_MAX_OVERFLOW | backend 10/20, worker/trainer 5/5 | Nếu đặt env, cùng giá trị ghi đè cả ba; tính tổng kết nối trước khi tăng worker |
| DATABASE_POOL_RECYCLE_SECONDS | 1800 | Tuổi kết nối pool trước tái tạo |
| LOG_LEVEL | INFO | Không bật DEBUG trên dữ liệu thật |

Nginx local có `client_max_body_size 25m`. Tăng MAX_IMAGE_SIZE_MB vượt giới hạn proxy **không đủ**: phải điều chỉnh Nginx và đánh giá RAM/đĩa/giới hạn upload tương ứng.

`ADMIN_INITIAL_PASSWORD` chỉ dùng một lần cho script khởi tạo, không lưu mật khẩu này trong cấu hình thường trực. Frontend chỉ nhận `NEXT_PUBLIC_API_BASE_URL=/api/v1`; không đặt secret vào biến NEXT_PUBLIC_*.

## Cấu hình động và cấu hình triển khai

Vòng đời mô hình → Cấu hình lưu chính sách huấn luyện trong database. Các trường upload/retry/poll chỉ đọc phản ánh cấu hình triển khai backend; không tự thay đổi môi trường worker. Thay env cần tạo lại đúng dịch vụ, không chỉ restart container giữ env cũ:

```text
docker compose --project-name elec_man --env-file .env up -d --force-recreate backend worker trainer
```

Thực hiện trong cửa sổ bảo trì và kiểm tra hàng đợi sau thay đổi. Không chạy lệnh trên khi migration/cấu hình HTTPS chưa sẵn sàng.

## Tránh cấu hình bị ghi đè ngoài ý muốn

Compose ưu tiên biến của shell hơn file env. Nếu tên biến đã được export từ lần thử trước, unset chúng trước khi khởi động. `docker compose config` thông thường có thể in mật khẩu; dùng `config --quiet` để xác minh. Xem [quy tắc nội suy chính thức](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).

Muốn chạy hai bản để thử, dùng project name, file env và cổng riêng; volume được gắn theo project. Ví dụ PowerShell:

```powershell
./scripts/start.ps1 -ProjectName elec_man_test -EnvFile .env.test-local -Port 8088 -Username admin_test
```

Không dùng tên project khác để khôi phục backup nếu chưa xác minh đúng volume. Image reader có tag chung giữa các project trên cùng Docker daemon; đây không phải cơ chế cách ly phiên bản image phục vụ production.
