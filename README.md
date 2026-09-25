# Hệ thống AI quản lý đồng hồ điện

Hệ thống web nội bộ dành cho các tài khoản quản trị, hỗ trợ xử lý ảnh đồng hồ điện theo lô, tự động xác nhận kết quả đủ tin cậy và kiểm duyệt phần còn lại.

## Trạng thái hiện tại

Nguyên mẫu có thể chạy gồm giao diện Next.js, backend FastAPI, PostgreSQL, migration Alembic, lưu trữ ảnh cục bộ có xác thực, hàng đợi tác vụ PostgreSQL, tiến trình OCR riêng, đối chiếu dữ liệu khách hàng, quy trình kiểm duyệt, bảng điều khiển, xuất JSON/Excel, proxy Nginx, nhật ký có cấu trúc và kiểm tra trạng thái dịch vụ.

## Khởi động

Sao chép `.env.example` thành `.env`, thay `POSTGRES_PASSWORD` và mật khẩu trong `DATABASE_URL` bằng cùng một mật khẩu mạnh, sau đó chạy:

```powershell
docker compose up --build
```

Mở `http://localhost/`. Endpoint kiểm tra hoạt động của backend là `/api/v1/health/live`; endpoint kiểm tra sẵn sàng là `/api/v1/health/ready`.

Để cài trên một máy mới từ đầu, làm theo [hướng dẫn cài đặt từng bước](docs/installation.md). Cấu trúc và quy ước đặt source code được mô tả trong [tài liệu cấu trúc](docs/source-structure.md).

## Migration và kiểm thử

Chạy migration bằng `docker compose exec backend alembic upgrade head`. Kiểm thử Python yêu cầu Python 3.12 trở lên cùng các dependency phát triển của backend, sau đó chạy `pytest backend/tests`.

## Khởi tạo quản trị viên

Sau khi áp dụng migration, truyền tạm thời `ADMIN_INITIAL_PASSWORD` vào lệnh khởi tạo trong container backend theo [hướng dẫn cài đặt](docs/installation.md). Sau khi đăng nhập, quản trị viên có thể thêm, sửa, khóa, xóa mềm và đổi mật khẩu tài khoản tại trang Quản trị. Đăng ký công khai chỉ tạo tài khoản chưa kích hoạt; một quản trị viên hiện hữu phải kích hoạt trước khi tài khoản có thể đăng nhập. Xem thêm [tài liệu bảo mật](docs/security.md). Hệ thống không cung cấp mật khẩu mặc định.

## Tải ảnh

Hệ thống hỗ trợ tải ảnh theo lô đã xác thực, mỗi yêu cầu tải một ảnh. Ảnh gốc được lưu cục bộ bằng tên UUID và chỉ có thể xem qua endpoint đã xác thực. Xem [tài liệu lưu trữ](docs/storage.md).

## Tác vụ xử lý

Hàng đợi dựa trên PostgreSQL xử lý ảnh bên ngoài yêu cầu HTTP. Xem [tài liệu tác vụ](docs/jobs.md).

## Quy trình AI

Mô hình phát triển hiện tại là `meter-ocr-baseline-v2-integer`, sử dụng OpenCV, mô hình ONNX dựng sẵn của RapidOCR và Tesseract làm phương án dự phòng. Kết quả đầy đủ có độ tin cậy lớn hơn ngưỡng cấu hình (mặc định 90%) và khớp mã khách hàng trong cơ sở dữ liệu được tự động xác nhận; phần còn lại phải kiểm duyệt thủ công. Đây chưa phải mô hình sản xuất đã được huấn luyện trên tập dữ liệu thực tế; xem [tài liệu quy trình AI](docs/ai-pipeline.md).

## Dữ liệu và huấn luyện

Ảnh tải lên và được con người xác nhận trong ứng dụng tự động trở thành mẫu đủ điều kiện trong PostgreSQL; không lưu nhãn khách hàng trong source code. Trainer độc lập chia dataset, huấn luyện bộ đọc chữ số, đánh giá validation và đăng ký artifact có checksum. Xem [hướng dẫn huấn luyện](docs/training.md). Một vài ảnh chỉ đủ thử pipeline, không đủ xác thực chất lượng sản xuất.

## Kiểm duyệt

Trang Vận hành hiển thị vùng tải ảnh toàn chiều ngang, sau đó là hàng chờ kiểm duyệt và danh sách đã xác nhận song song. Trang Các lô dữ liệu cho phép mở từng lô để xem danh sách ảnh, trạng thái và kết quả nhận diện. Hệ thống tách biệt đầu ra AI bất biến với giá trị cuối cùng, đồng thời ghi lại mọi xác nhận, từ chối và chỉnh sửa; xem [tài liệu kiểm duyệt](docs/review.md).

## Bảng điều khiển và xuất dữ liệu

Bảng điều khiển cung cấp số liệu tổng hợp công khai ở chế độ chỉ xem. Quản trị viên nhập danh sách khách hàng JSON và tạo đồng thời báo cáo JSON, Excel theo tháng tại trang Quản trị. Hai tệp xuất có cùng bảy trường như dữ liệu khách hàng đầu vào; xem [tài liệu xuất dữ liệu](docs/export.md).

## Quản trị và sao lưu

Hệ thống gồm cấu hình có kiểm toán, kho mô hình được xác minh checksum, đánh giá AI vận hành và lịch sử kiểm toán. Xem [tài liệu quản trị](docs/administration.md) và [sao lưu/khôi phục](docs/backup-restore.md).

PostgreSQL chủ động không mở cổng ra ngoài. Trong môi trường sản xuất, hãy dùng endpoint HTTPS nội bộ và chỉ bật HSTS sau khi TLS được xác minh. Docker Desktop phải đang chạy trước khi build hoặc khởi động hệ thống.
