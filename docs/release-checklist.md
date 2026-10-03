# Checklist phát hành

## Cổng chất lượng tự động

Mỗi pull request và lần đẩy lên `master` hoặc `codex/**` phải hoàn thành workflow `Kiểm thử và build`:

- Backend: Ruff, kiểm tra format và toàn bộ pytest.
- Frontend: typecheck, ESLint, unit test và production build.
- AI: build đúng image production rồi chạy bộ test trong image riêng.
- Hạ tầng: xác thực cấu hình Docker Compose.
- Bí mật: chặn khóa riêng và token phổ biến bị commit nhầm.

CodeQL phân tích Python và JavaScript/TypeScript ở pull request, nhánh chính và theo lịch hằng tuần. Dependabot kiểm tra dependency Python, npm, Docker và GitHub Actions hằng tuần.

## Trước khi go-live

1. Tất cả workflow GitHub phải xanh trên đúng commit phát hành.
2. Thay toàn bộ secret mẫu; không lưu `.env` vào Git.
3. Cấu hình domain HTTPS, CORS/host chính xác và bật cookie `Secure`.
4. Chạy migration trên bản sao dữ liệu, sau đó mới chạy ở production.
5. Tạo backup và chạy `verify-backup` trước khi triển khai.
6. Kiểm tra `/api/v1/health/live` và `/api/v1/health/ready` sau triển khai.
7. Đăng nhập bằng tài khoản VIEWER và ADMIN để kiểm tra lại phân quyền.
8. Upload một lô nhỏ, kiểm duyệt, xác nhận và xuất JSON/Excel đầu-cuối.
9. Chỉ bật tự động xác nhận khi tập validation độc lập đạt ngưỡng đã phê duyệt.
10. Cấu hình cảnh báo lỗi, dung lượng lưu trữ, backup thất bại và hàng đợi bị kẹt.

## Điều kiện quay lui

Quay về image/commit trước nếu health check thất bại, migration không hoàn tất, tỷ lệ lỗi xử lý tăng bất thường hoặc dữ liệu xác nhận không được ghi đầy đủ. Không phục hồi database cũ khi chưa dừng lưu lượng và xác minh đúng bản backup.
