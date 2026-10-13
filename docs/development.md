# Phát triển và đóng góp

## Quy trình

Lấy master mới nhất, tạo nhánh thay đổi riêng, không sửa dữ liệu thật để test. Khởi chạy một project Compose riêng nếu cần UI/API. Không trộn backup hoặc ảnh khách hàng vào pull request.

Đọc [kiến trúc](architecture.md), [quyền](roles.md) và [quy trình review](review.md) trước khi đổi nghiệp vụ. Repo chưa có giấy phép mã nguồn tổng quát; thống nhất quyền sử dụng/phân phối với chủ dự án trước khi phân phối lại. Dependency và trọng số có giấy phép riêng; không coi repo là cấp phép lại chúng.

## Backend

Python ≥3.12; tạo virtualenv rồi cài dependency phát triển:

```text
python -m venv .venv
python -m pip install -e "./backend[dev]"
python -m pytest backend/tests -q
python -m ruff check backend/app backend/tests
python -m ruff format --check backend/app backend/tests
```

Kích hoạt venv tương ứng OS trước các lệnh pip; trong Docker người dùng cuối không cần venv. Không đặt DATABASE_URL của production khi chạy test; test runner integration chủ động tạo PostgreSQL tạm.

## Frontend

Node 22 theo CI, dùng lockfile:

```text
npm --prefix frontend ci
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
```

Không dùng npm install để thay lockfile vô tình. Không đặt secret trong NEXT_PUBLIC_*. Tương tác phải xử lý trạng thái loading/error/empty, bàn phím, bản nháp chưa lưu và response cũ tới muộn.

## Migration

Thêm revision mới, không chỉnh schema bằng tay ngoài Alembic. Test upgrade từ database trống và kiểm thử dữ liệu cũ phù hợp. Không dùng downgrade production làm cơ chế rollback code; đọc giới hạn mất dữ liệu/quyền trong từng migration.

## Kiểm tra trước commit

```text
python scripts/check-repository-secrets.py
python scripts/check_docs.py
git diff --check
git status --short
```

Chạy đầy đủ test liên quan và CI. Kiểm tra staged file không có dữ liệu private/binary ngoài ý muốn. Quét secret theo pattern không bảo đảm bắt được tất cả PII; vẫn phải review thủ công. Không in docker compose config chứa secret vào issue.

Mô tả rõ tests thực sự chạy và giới hạn; không gọi unit tests xanh là AI chính xác hoặc hệ thống được chứng nhận bảo mật/pháp lý.
