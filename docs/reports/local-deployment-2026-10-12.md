# Cập nhật localhost — 12/10/2026

> Báo cáo lịch sử theo ngày, không phải hướng dẫn bản hiện hành. Xem [danh mục tài liệu](../README.md).

Đã build source hiện tại và tạo lại backend, frontend, worker, trainer.
Không reset database, không xóa volume/ảnh/nhãn, không kích hoạt hoặc huấn luyện mô hình mới.

- Sao lưu database: `backups/audit-20261012-170541/database.dump`.
- Kiểm tra cấu trúc archive bằng `pg_restore --list`: thành công; chưa thử phục hồi đầy đủ.
- Alembic ở revision `20261005_0027`.
- `/`, `/api/v1/health/ready`, `/api/v1/dashboard`: HTTP 200 sau cập nhật.
- Backend/frontend/PostgreSQL/hai reader: healthy; worker/trainer đang chạy.
- Dữ liệu trước/sau giữ nguyên: 660 khách hàng, 61 ảnh, 37 bản ghi LABELED/CONFIRMED.
- SHA-256 localization.py trong worker trùng source:
  `5a18fabf1801c239eab2f4fe9a7b352461ae41a64be97118686fc9c634757c6e`.

Các container ứng dụng cũ được thay bằng container mới. Không dọn image thử nghiệm,
không xóa lịch sử mô hình hoặc dữ liệu; không ảnh hưởng các dự án Docker khác.
Đây là cập nhật chạy cục bộ tại http://localhost/, không phải triển khai internet.
Mức chính xác AI vẫn có giới hạn đã ghi trong báo cáo chẩn đoán; giữ kiểm duyệt.
