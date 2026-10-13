# Kiến trúc hệ thống

## Thành phần

```text
Trình duyệt → Nginx → Next.js
                  → FastAPI → PostgreSQL
                         ↘ kho ảnh (volume)
PostgreSQL job queue → worker → PP-OCR reader
                            → PARSeq reader
PostgreSQL training queue → trainer → kho model/dataset (volume)
```

Nginx là cổng vào duy nhất. PostgreSQL không publish cổng host; reader không có database hoặc volume ảnh. Frontend không giữ secret/backend credentials.

| Dịch vụ Compose | Nhiệm vụ |
|---|---|
| postgres | Khách hàng, tài khoản/phiên/audit, metadata ảnh, nhãn, job/train queue, chỉ số tháng/ảnh BYTEA |
| storage-init / model-init | Cấp quyền volume cho UID 10001, chạy một lần |
| migrate | Alembic upgrade head trước ứng dụng, chạy một lần |
| seed | Kiểm tra/import snapshot đã được phép vào database mới; bỏ qua database có tài khoản/nghiệp vụ |
| backend | API, xác thực/phân quyền/CSRF, upload, review, dashboard, report |
| worker | Nhận job có khóa SKIP LOCKED, chạy pipeline và lưu đề xuất bất biến |
| reader-ppocr / reader-parseq | Model pretrained nạp trong tiến trình, trả chuỗi số |
| trainer | Đóng băng dataset, học định vị trong mặt công tơ/fine-tune PARSeq/export crop/benchmark holdout, registry TESTING |
| frontend | UI tiếng Việt, dữ liệu/API cùng origin, route theo vai trò |
| nginx | Proxy, giới hạn request, security headers, healthcheck đường vào |

## Vòng đời dữ liệu

Upload tạo metadata/file gốc/job. Job thành công lưu kết quả AI, **không** tạo chỉ số tháng. Con người lưu vùng/nhãn riêng để học; xác nhận mã+số+tháng tạo bản ghi nghiệp vụ và bản sao ảnh chuẩn tên khách hàng. Dashboard/export dùng bảng đã xác nhận. Từ chối/sửa dữ liệu có audit và kiểm soát revision.

Ba volume lâu dài: postgres_data, storage_data, model_data, đều có tiền tố project. Không có volume log; stdout được Docker xoay vòng. Mạng edge dùng frontend/nginx, application nối nginx/backend, data internal nối các tiến trình dữ liệu.

## Giới hạn thiết kế

Đây là triển khai một host bằng Compose, không phải cluster HA. Login rate limit lưu bộ nhớ một API process; scale nhiều replica cần limiter chung. PostgreSQL và file volume không có distributed transaction; thao tác file có cleanup khi rollback nhưng crash cứng có thể để bản sao dư. Backup cần tạm dừng writer để nhất quán cả ba kho.

Job/training có khóa và kiểm thử cạnh tranh trên PostgreSQL; điều đó không chứng minh mọi mức tải lớn đều đạt SLA. Fine-tune PARSeq đã tích hợp, nhưng chưa có mô hình chuyên biệt đạt kiểm định thực địa. Tự xác nhận vẫn khóa. Trainer chạy một replica, mặc định giới hạn 1 CPU/2 GiB, tách ABI NumPy khỏi worker. Xem [bảo mật](security.md), [backup](backup-restore.md) và [pipeline](ai-pipeline.md).
