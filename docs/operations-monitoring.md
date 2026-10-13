# Giám sát và sao lưu vận hành

## Màn hình Giám sát

SUPER_ADMIN vào Vòng đời mô hình → Giám sát. API `/api/v1/training/health` chỉ đọc, bị phân quyền tại server. Làm mới 30 giây khi tab đang mở, dừng polling khi chuyển tab. Không trả DSN, password, stacktrace, dữ liệu khách hàng hoặc đường dẫn kho riêng.

Có số job chờ/đang xử lý, job quá hạn, lỗi 24 giờ, thời gian chờ cũ nhất; độ trễ p50/p95 của tối đa 500 job hoàn tất; trạng thái/tiến trình/heartbeat stage train; dung lượng trống kho ảnh/model; trạng thái backup đã verify. Cảnh báo khi job quá hạn, hàng đợi lâu, lỗi mới, đĩa dưới 10%, backup chưa verify hoặc quá 26 giờ.

Số job không phải heartbeat worker; cần xem Docker health/log khi worker không nhận việc. Dung lượng Docker volume có thể chung filesystem, không cộng hai số trống thành tổng dung lượng máy. Đây chưa phải hệ thống cảnh báo ngoài trang web: cần tích hợp dịch vụ giám sát hạ tầng/mail phù hợp trước Internet production.

## Backup quản lý tự động

Python 3.12+ trên host và Docker đang chạy:

```text
python scripts/managed_backup.py --project elec_man
```

Helper không cần đọc/tạo `.env`: xác minh container Compose thật, nhãn owner volume và đúng project. Khóa file OS ngăn hai backup trùng nhau; bỏ qua container test chỉ kế thừa nhãn image. Tạm dừng chính xác backend/worker/trainer đang chạy, pg_dump database, đọc hai volume bằng UID 10001/chỉ đọc và stream về file host. Luôn thử bật lại writer trong finally; không gắn Docker socket vào ứng dụng.

Backup nằm trong `backups/<UTC>-<ID>/` gồm database.sql, storage.tar.gz, models.tar.gz, checksums.sha256, managed-manifest.json. Chỉ coi thành công sau hash/đường dẫn archive hợp lệ. Thất bại để lại bản dở cho chẩn đoán, không ghi manifest verified. Trạng thái tối giản lưu `.maintenance/backup-status.json` để UI hiển thị, không có secret/path.

**Có cửa sổ ngừng ghi ngắn trong mỗi lần backup**; chọn giờ ít tải, không hứa zero downtime. Bản SQL có tài khoản/hash/phiên thật, là dữ liệu riêng, **không đẩy lên GitHub PUBLIC**. Trên Linux dùng umask 077, trên Windows hạn chế ACL thư mục cho chủ dự án. Backup không chứa `.env`/TLS: giữ cấu hình gốc trong kho mã hóa riêng.

## Đặt lịch

Có hai cách, không cần thay mã ứng dụng:

1. Task Scheduler Windows/systemd timer Linux gọi lệnh backup mỗi ngày, đặt working directory là root repo. Chọn tài khoản có quyền Docker và đúng volume; bật chạy bù nếu bỏ lỡ, không chạy song song. Không nhập secret vào arguments.
2. Supervisor host chạy vòng lặp:

```text
python scripts/managed_backup.py --project elec_man --watch --interval-hours 24
```

`--watch` chạy bản đầu ngay rồi chờ đủ khoảng sau mỗi lần. Phải giữ tiến trình qua supervisor/restart máy; không mặc nhiên đã đặt Task Scheduler chỉ vì đã chạy backup một lần. Theo dõi exit/log và trạng thái UI.

Mặc định không xóa backup. Khi đã có bản sao ngoài máy và muốn chính sách giữ bản mới nhất:

```text
python scripts/managed_backup.py --project elec_man --watch --interval-hours 24 --keep 7
```

**`--keep 7` cho phép xóa vĩnh viễn backup managed cũ hơn 7 bản mới nhất**, sau một backup mới thành công. Chỉ xóa thư mục phẳng đúng tên, project/format/verified, đầy đủ payload và checksum khớp, đường dẫn nằm dưới BackupRoot. Không chạm backup lịch sử do công cụ khác tạo, tệp bất thường hoặc bản dở. Không dùng cờ này nếu chưa hiểu retention và chưa có bản ngoài máy. Lần cải tiến này không xóa backup thật.

## Ngoài máy chủ và diễn tập

Cần bạn chọn NAS/object storage/thư mục mã hóa và tài khoản nhận trước khi tự động chuyển dữ liệu riêng ra ngoài. Chưa cấu hình đích ngoài máy trong repo, không giả vờ đã có backup 3-2-1. Sau mỗi lần chuyển verify checksum; diễn tập khôi phục ít nhất hàng tháng bằng [hướng dẫn phục hồi](backup-restore.md).

## Cập nhật local khi thất lạc .env

`start.ps1/start.sh` cố ý từ chối tạo secret mới nếu đã có volume. Nếu các container local loopback vẫn giữ cấu hình gốc, đã build image mới và có Python host:

```text
python scripts/update_running.py --project elec_man
```

Helper lấy env gốc **trong bộ nhớ**, giữ cả giới hạn pool từng service, backup đầy đủ, dừng writer, migration, recreate/chờ readiness. Không ghi `.env` hoặc in secret. Chỉ hỗ trợ Compose local HTTP bind loopback của repo; không dùng với override HTTPS/custom mounts/scale. Với production phải dùng cấu hình/override gốc đã mã hóa. Nếu cập nhật thất bại, backup còn nguyên nhưng không tự rollback database; kiểm tra log riêng và không suy đoán đã phục hồi thành công.
