# Kiểm thử và xác minh

Kiểm thử logic phần mềm, cài đặt và AI là các phạm vi khác nhau. Test xanh không chứng minh độ chính xác ảnh thực tế, đáp ứng mọi mức tải hoặc bảo mật/pháp lý tuyệt đối.

## Backend và công cụ

Python ≥3.12, dependency ./backend[dev]:

```text
python -m pytest backend/tests -q
python -m ruff check backend/app backend/tests backend/alembic ai scripts
python -m ruff format --check backend/app backend/tests backend/alembic ai scripts
python scripts/check-repository-secrets.py
python scripts/check_docs.py
```

Backend có regression cho auth/roles/CSRF, upload/path, review/revision/rollback, report/dashboard/tariff, training/model gates, bootstrap và backup archive safety. Warnings deprecation của TestClient/httpx có thể còn; không che warning bằng coi test thất bại là thành công.

## Integration PostgreSQL

```text
python scripts/test-integration.py
```

Runner tạo PostgreSQL 16 tên ngẫu nhiên, chỉ bind loopback, database/schema/ảnh thử, chạy toàn bộ migration và API tests, tự dọn. Không đặt ELEC_MAN_INTEGRATION=1 để chạy trực tiếp database thật.

OCR integration API dùng fixture ở đầu ra worker: kiểm tra contract/job/transaction, không benchmark model. Kịch bản gồm guest/3roles, cookie/session/CSRF, upload sai/đúng, lưu nhãn chưa có mã, tháng bắt buộc, concurrent same-month/stale revision, audit, export, reject/reopen và billing theo phiên bản.

## AI trong image đúng dependency

```text
docker build --tag elec_man-ai-ci-base --file ai/Dockerfile .
docker build --tag elec_man-ai-ci-test --file ai/Dockerfile.test .
docker run --rm --network none --env SESSION_SECRET=ci-only-session-secret-at-least-32-characters elec_man-ai-ci-test
```

Image test sao chép source lúc build. Sau chỉnh AI phải build lại, không dùng image test cũ để chứng minh source mới. Tests này chủ yếu pipeline/dataset contracts; accuracy cần tập test độc lập.

## Frontend

```text
npm --prefix frontend ci
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend audit
```

Node tests kiểm logic thuần như trạng thái, quyền, dialog gate; không phải toàn bộ browser E2E. Kiểm thêm desktop/mobile, zoom/4góc, bàn phím/dialog, phân trang, bản nháp và UI refresh.

## Sandbox không có dữ liệu thật

```text
python scripts/verification_sandbox.py --minutes 30
python scripts/verification_sandbox.py --https --probe --report .codex-tmp/https-verification.json
```

Cần image backend/frontend đã build và dependency dev. Sandbox tự dọn, không dùng tài khoản thật; ảnh/OCR fixture. Report HTTPS cục bộ xác minh cookie/header/proxy, không xác minh CA/DNS Internet.

Kiểm fresh-install bằng project/cổng/env riêng rồi dùng chỉ dữ liệu giả. Thử boot lần hai giữ secret/tài khoản, missing-env fail-closed, login/import/upload/worker/review/monthreport thật. **Hai reader thật** chỉ xác minh chúng nhận/chạy/trả contract trên ảnh thử; không suy thành accuracy công tơ.

## Backup và CI

Verify manifest + archive safety, diễn tập restore ở resource tạm theo [backup](backup-restore.md). Không dùng backup SQL không tin cậy.

CI trên push master/PR kiểm secret, docs/bootstrap, backend, integration, frontend, AI và Compose; CodeQL workflow riêng. Kết quả phải gắn commit cụ thể. Các số test/bộ đo cũ đặt ở docs/reports, không dùng số cũ như số của HEAD.

Xem [checklist](release-checklist.md), [báo cáo ngày 13/10](reports/final-verification-2026-10-13.md).
