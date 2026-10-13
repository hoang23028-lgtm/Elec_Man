# Sao lưu và khôi phục

Ưu tiên helper mới [backup có khóa/tạm dừng writer/verify/đặt lịch](operations-monitoring.md): `python scripts/managed_backup.py --project elec_man`. Các script PS/sh bên dưới là công cụ cấp thấp, không tự dừng writer hoặc đặt lịch; phải quản lý cửa sổ bảo trì riêng khi dùng chúng.

## Diễn tập không ghi đè dữ liệu thật

Sau khi có một bản backup đầy đủ, dùng Python 3.12 trở lên và Docker để thử
phục hồi vào PostgreSQL/thư mục tạm mới:

```powershell
python scripts/rehearse_backup.py backups/20261013T045240Z --database-user electric_meter_app --output .codex-tmp/restore-check.json
```

Thay thư mục và tên role bằng cấu hình backup của bạn; đây là tên PostgreSQL,
không phải mật khẩu. Chọn tệp báo cáo mới mỗi lần. Script không mở cổng database,
không gắn volume production, kiểm tra hash từng tệp sau giải nén và tự dọn tài
nguyên. Chỉ dùng SQL backup do hệ thống tạo, không chạy dump từ nguồn không tin
cậy vì SQL là mã thực thi. Diễn tập thành công ngày 13/10 được ghi trong
[báo cáo kiểm tra](reports/final-verification-2026-10-13.md).

## Sao lưu và phục hồi thực tế

Để database và ảnh/mô hình cùng mốc dữ liệu, tạm dừng các dịch vụ ghi
`backend`, `worker`, `trainer` trong cửa sổ bảo trì khi sao lưu đầy đủ, rồi bật
lại. `pg_dump` nhất quán riêng database, không tự làm nhất quán các kho tệp.
Sau phục hồi SQL/kho ảnh/kho mô hình phải đều thành công mới bật lại ứng dụng;
ba thành phần này không có transaction chung. Luôn giữ một backup hiện trạng
trước khi phục hồi đè.

Sao lưu PostgreSQL, vùng lưu trữ ảnh gốc/phái sinh và các gói mô hình thành những thành phần riêng. Bản sao lưu được ghi bên dưới `backups/<mốc thời gian UTC>/` cùng checksum SHA-256.

Môi trường phát triển Windows:

```powershell
.\scripts\backup.ps1 -EnvFile .env
```

Môi trường sản xuất Ubuntu:

```bash
ENV_FILE=.env sh scripts/backup.sh
```

Sao chép thư mục sao lưu hoàn tất sang vùng lưu trữ riêng hoặc NAS. Bản sao chỉ nằm trên máy chủ ứng dụng là chưa đủ an toàn.

Xác minh checksum và khả năng đọc hai kho nén trước khi chuyển bản sao hoặc phục hồi:

```powershell
.\scripts\verify-backup.ps1 -BackupDirectory .\backups\20260918T120000Z
```

```bash
sh scripts/verify-backup.sh ./backups/20260918T120000Z
```

Áp dụng quy tắc 3-2-1: tối thiểu ba bản sao, trên hai loại thiết bị, một bản nằm ngoài máy chủ. Mã hóa thư mục backup ở tầng ổ đĩa hoặc kho lưu trữ vì database dump và ảnh có dữ liệu nghiệp vụ. Giới hạn tài khoản đọc, bật cảnh báo khi script thất bại và kiểm tra `checksums.sha256` sau mỗi lần chuyển. Cấu hình Task Scheduler/cron chạy backup hằng ngày, giữ tối thiểu 7 bản gần nhất và diễn tập khôi phục hằng tháng trên máy không phải production. Script chỉ cung cấp cơ chế sao lưu; việc đặt lịch, chuyển bản sao ra ngoài máy và cảnh báo thất bại là bước vận hành bắt buộc trước khi go-live.

Khôi phục là thao tác phá hủy dữ liệu hiện tại và chủ động yêu cầu công tắc xác nhận rõ ràng. Trước tiên hãy dừng lưu lượng người dùng, xác minh đúng mốc thời gian rồi chạy:

```powershell
.\scripts\restore.ps1 -BackupDirectory .\backups\20260918T120000Z -EnvFile .env -ConfirmRestore
```

Script khôi phục xác minh checksum, dừng các dịch vụ ứng dụng, thay thế schema cơ sở dữ liệu và volume lưu trữ/mô hình rồi khởi động lại hệ thống. Hãy kiểm thử khôi phục định kỳ trên máy chủ không phải production. Không dùng bản sao trực tiếp của thư mục dữ liệu PostgreSQL đang hoạt động làm bản sao lưu chính.

Để cài mô hình ứng viên vào volume mô hình được bảo vệ, chạy `install-model.ps1`, ghi lại SHA-256 được trả về rồi đăng ký đường dẫn tương đối và checksum trong giao diện quản trị. Đăng ký không đồng nghĩa với kích hoạt hoặc nạp nóng mô hình.

## Tính an toàn của bộ công cụ

Chạy từ root repo, luôn chỉ định đúng ProjectName/COMPOSE_PROJECT_NAME nếu khác elec_man. PowerShell backup/restore yêu cầu PowerShell 7 (utf8NoBOM). Linux backup dùng sh và Docker; tên volume được kiểm tra nhãn owner trước sao lưu. Không có restore.sh; trên Linux dùng PowerShell 7 chạy restore.ps1 hoặc diễn tập chuyển dữ liệu trước khi xây quy trình restore theo hạ tầng.

Verify trên cả hai OS dùng image elec_man-backend:latest đã build và scripts/verify_backup.py: kiểm manifest đúng ba payload, hash, file liên kết, đường dẫn tuyệt đối/traversal, symlink/hardlink/member trùng trong archive, tổng dung lượng/entry count. Nó không xác minh nội dung SQL là vô hại; chỉ dùng dump đáng tin cậy. Docker verifier chạy network none, mount chỉ đọc.

Các script mặc định dùng Compose local. Với file override production, đặt COMPOSE_FILE theo đúng hai file và kiểm tra env/project trước khi chạy; không bỏ override khiến startup sau restore chuyển nhầm về HTTP. Ghi tên PostgreSQL role đúng của dump để diễn tập, không dùng tên tài khoản web thay thế.

.env/cert TLS không nằm trong ba payload backup tự động; giữ bản cấu hình/khóa riêng trong kho mã hóa để phục hồi đúng mật khẩu database và session. Cài máy mới rồi chuyển backup không có nghĩa phải publish backup lên GitHub.
