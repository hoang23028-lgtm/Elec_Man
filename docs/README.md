# Danh mục tài liệu

Tài liệu trong thư mục này mô tả **bản mã nguồn hiện hành**. Báo cáo theo ngày ở reports/ chỉ phản ánh trạng thái tại ngày đo; có thể chứa phát hiện đã được sửa, không phải hướng dẫn vận hành mới nhất.

## Bắt đầu và sử dụng

- [Cài trên máy mới](installation.md): chuẩn bị Docker, một lệnh khởi động, quản trị đầu tiên, xử lý lỗi.
- [Hướng dẫn sử dụng](usage.md): khách hàng → upload → khoanh/lưu nhãn → xác nhận tháng → thống kê/báo cáo.
- [Cấu hình](configuration.md): env, phạm vi hiệu lực, cổng/origin, secret.
- [Phân quyền](roles.md): guest/VIEWER/ADMIN/SUPER_ADMIN.
- [Quản trị](administration.md), [kiểm duyệt](review.md), [xuất JSON/Excel](export.md).

## Kỹ thuật và AI

- [Kiến trúc](architecture.md), [tổ chức source](source-structure.md), [phát triển](development.md).
- [Kho ảnh/database](storage.md), [hàng đợi](jobs.md).
- [Pipeline AI](ai-pipeline.md), [huấn luyện](training.md), [độ tin cậy](ai-reliability.md).
- [Kiểm thử](testing.md), [checklist phát hành](release-checklist.md).

## Triển khai và bảo vệ dữ liệu

- [Cập nhật/HTTPS](deployment.md), [bảo mật](security.md), [sao lưu/khôi phục](backup-restore.md).
- [Nguồn tham khảo UI/UX](ui-ux-references.md); tài liệu thiết kế ở [design-system](../design-system/electricity-meter-ai/MASTER.md).

## Báo cáo lịch sử

- [Chẩn đoán nhãn 29/09](reports/label-diagnosis-2026-09-29.md).
- [Benchmark reader 01/10](reports/modern-reader-benchmark-2026-10-01.md).
- [Hiệu năng/model 01/10](reports/performance-and-model-review-2026-10-01.md).
- [Rà soát hệ thống 05/10](reports/system-audit-2026-10-05.md).
- [Chẩn đoán AI 12/10](reports/ai-diagnostic-2026-10-12.md).
- [Chính sách tính tiền 12/10](reports/billing-policy-2026-10-12.md).
- [Tính toàn vẹn chỉ số tháng 12/10](reports/monthly-integrity-2026-10-12.md).
- [Triển khai local 12/10](reports/local-deployment-2026-10-12.md).
- [Kiểm tra UI 12/10](reports/ui-verification-2026-10-12.md).
- [Xác minh toàn hệ thống 13/10](reports/final-verification-2026-10-13.md).
- [Xác minh bản chia sẻ 13/10](reports/sharing-verification-2026-10-13.md).

Không kèm dữ liệu khách hàng, ảnh/nhãn, backup hoặc trọng số riêng trong Git. Mẫu examples/customers.json là giả. Điều kiện AI/HTTPS/privacy còn lại phải đọc trước khi triển khai rộng.
