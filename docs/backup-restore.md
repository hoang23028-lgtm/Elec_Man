# Sao lưu và khôi phục

Sao lưu PostgreSQL, vùng lưu trữ ảnh gốc/phái sinh và các gói mô hình thành những thành phần riêng. Bản sao lưu được ghi bên dưới `backups/<mốc thời gian UTC>/` cùng checksum SHA-256.

Môi trường phát triển Windows:

```powershell
.\scripts\backup.ps1 -EnvFile .env.example
```

Môi trường sản xuất Ubuntu:

```bash
ENV_FILE=.env ./scripts/backup.sh
```

Sao chép thư mục sao lưu hoàn tất sang vùng lưu trữ riêng hoặc NAS. Bản sao chỉ nằm trên máy chủ ứng dụng là chưa đủ an toàn.

Khôi phục là thao tác phá hủy dữ liệu hiện tại và chủ động yêu cầu công tắc xác nhận rõ ràng. Trước tiên hãy dừng lưu lượng người dùng, xác minh đúng mốc thời gian rồi chạy:

```powershell
.\scripts\restore.ps1 -BackupDirectory .\backups\20260918T120000Z -EnvFile .env -ConfirmRestore
```

Script khôi phục xác minh checksum, dừng các dịch vụ ứng dụng, thay thế schema cơ sở dữ liệu và volume lưu trữ/mô hình rồi khởi động lại hệ thống. Hãy kiểm thử khôi phục định kỳ trên máy chủ không phải production. Không dùng bản sao trực tiếp của thư mục dữ liệu PostgreSQL đang hoạt động làm bản sao lưu chính.

Để cài mô hình ứng viên vào volume mô hình được bảo vệ, chạy `install-model.ps1`, ghi lại SHA-256 được trả về rồi đăng ký đường dẫn tương đối và checksum trong giao diện quản trị. Đăng ký không đồng nghĩa với kích hoạt hoặc nạp nóng mô hình.
