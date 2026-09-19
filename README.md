# Hệ thống AI quản lý đồng hồ điện

Hệ thống web nội bộ dành cho một quản trị viên, hỗ trợ xử lý ảnh đồng hồ điện theo lô một cách an toàn và kiểm duyệt kết quả thủ công.

## Trạng thái hiện tại

Nguyên mẫu có thể chạy gồm giao diện Next.js, backend FastAPI, PostgreSQL, migration Alembic, lưu trữ ảnh cục bộ có xác thực, hàng đợi tác vụ PostgreSQL, tiến trình OCR riêng, quy trình kiểm duyệt, bảng điều khiển, xuất Excel, proxy Nginx, nhật ký có cấu trúc và kiểm tra trạng thái dịch vụ.

## Khởi động

Sao chép `.env.example` thành `.env`, thay `POSTGRES_PASSWORD` và mật khẩu trong `DATABASE_URL` bằng cùng một mật khẩu mạnh, sau đó chạy:

```powershell
docker compose up --build
```

Mở `http://localhost/`. Endpoint kiểm tra hoạt động của backend là `/api/v1/health/live`; endpoint kiểm tra sẵn sàng là `/api/v1/health/ready`.

## Migration và kiểm thử

Chạy migration bằng `docker compose exec backend alembic upgrade head`. Kiểm thử Python yêu cầu Python 3.12 trở lên cùng các dependency phát triển của backend, sau đó chạy `pytest backend/tests`.

## Khởi tạo quản trị viên

Sau khi áp dụng migration, đặt tạm thời `ADMIN_INITIAL_PASSWORD` rồi chạy `python -m app.scripts.init_admin --username <ten_dang_nhap>` trong container backend. Xem [tài liệu bảo mật](docs/security.md). Hệ thống chủ động không cung cấp endpoint đăng ký hoặc mật khẩu quản trị mặc định.

## Tải ảnh

Hệ thống hỗ trợ tải ảnh theo lô đã xác thực, mỗi yêu cầu tải một ảnh. Ảnh gốc được lưu cục bộ bằng tên UUID và chỉ có thể xem qua endpoint đã xác thực. Xem [tài liệu lưu trữ](docs/storage.md).

## Tác vụ xử lý

Hàng đợi dựa trên PostgreSQL xử lý ảnh bên ngoài yêu cầu HTTP. Xem [tài liệu tác vụ](docs/jobs.md).

## Quy trình AI

Mô hình phát triển hiện tại là `meter-ocr-baseline-v1`, sử dụng OpenCV, mô hình ONNX dựng sẵn của RapidOCR và Tesseract làm phương án dự phòng. Mọi kết quả đều phải được kiểm duyệt thủ công và không được mô tả đây là mô hình sản xuất đã huấn luyện; xem [tài liệu quy trình AI](docs/ai-pipeline.md).

## Dữ liệu huấn luyện

Nhãn mẫu đã được phê duyệt được ghi trong `training/annotations.jsonl` mà không lưu ảnh nguồn. Mẫu được gán nhãn đầu tiên được mô tả trong [hướng dẫn huấn luyện](docs/training.md). Một ảnh đã gán nhãn không đủ để huấn luyện hoặc xác thực mô hình nhận dạng thực tế.

## Kiểm duyệt

Hệ thống tách biệt đầu ra AI bất biến với giá trị cuối cùng đã kiểm duyệt và ghi lại mọi chỉnh sửa; xem [tài liệu kiểm duyệt](docs/review.md).

## Bảng điều khiển và xuất dữ liệu

Bảng điều khiển cung cấp số liệu tổng hợp công khai ở chế độ chỉ xem. Quản trị viên có thể xuất chỉ số cuối cùng đã xác nhận ra Excel; xem [tài liệu xuất dữ liệu](docs/export.md).

## Quản trị và sao lưu

Hệ thống gồm cấu hình có kiểm toán, kho mô hình được xác minh checksum, đánh giá AI vận hành và lịch sử kiểm toán. Xem [tài liệu quản trị](docs/administration.md) và [sao lưu/khôi phục](docs/backup-restore.md).

PostgreSQL chủ động không mở cổng ra ngoài. Trong môi trường sản xuất, hãy dùng endpoint HTTPS nội bộ và chỉ bật HSTS sau khi TLS được xác minh. Docker Desktop phải đang chạy trước khi build hoặc khởi động hệ thống.
