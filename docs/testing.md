# Kiểm thử và xác minh

Các kiểm thử dataset/holdout mới nằm ở `backend/tests/test_dataset_policy.py`, `backend/integration_tests/test_dataset_annotations.py`; gate ở backend và `frontend/tests/model-activation-gate.test.mjs`. Smoke optimizer/checkpoint thực tế dùng [hướng dẫn train](training.md). Backup có thêm kiểm tra khóa OS, retention theo owner và bật lại writer khi lỗi.

Để thử upload/đọc API đồng thời với 20 epoch tối ưu PARSeq trên **ảnh giả**, sau khi build backend/frontend/trainer:

```text
python scripts/mixed_workload_probe.py --output .codex-tmp/mixed-workload-new.json
```

Script tự tạo sandbox, không nhận URL hệ thống thật, không gắn volume/DB thật; ghi số epoch thực sự chồng lên thời gian HTTP. Nó không đo throughput OCR ảnh thật, huấn luyện dataset lớn hoặc chứng nhận SLA. Kiểm thử HTTPS độc lập vẫn dùng `verification_sandbox.py --https --probe`.

Kiểm thử logic phần mềm, cài đặt và AI là các phạm vi khác nhau. Test xanh không chứng minh độ chính xác ảnh thực tế, đáp ứng mọi mức tải hoặc bảo mật/pháp lý tuyệt đối.

## Backend và công cụ

Python ≥3.12, dependency ./backend[dev]:

```text
python -m pytest backend/tests -q
python -m ruff check backend/app backend/tests backend/alembic ai scripts
python -m ruff format --check backend/app backend/tests backend/alembic ai scripts
python scripts/check-repository-secrets.py
python scripts/check_docs.py
python scripts/check_shared_data.py
```

Backend có regression cho auth/roles/CSRF, upload/path, review/revision/rollback, report/dashboard/tariff, training/model gates, bootstrap và backup archive safety. Warnings deprecation của TestClient/httpx có thể còn; không che warning bằng coi test thất bại là thành công.

## Integration PostgreSQL

```text
python scripts/test-integration.py
```

Runner tạo PostgreSQL 16 tên ngẫu nhiên, chỉ bind loopback, database/schema/ảnh thử, chạy toàn bộ migration và API tests, tự dọn. Không đặt ELEC_MAN_INTEGRATION=1 để chạy trực tiếp database thật.

OCR integration API dùng fixture ở đầu ra worker: kiểm tra contract/job/transaction, không benchmark model. Kịch bản gồm guest/3roles, cookie/session/CSRF, upload sai/đúng, lưu nhãn chưa có mã, tháng bắt buộc, concurrent same-month/stale revision, audit, export, reject/reopen và billing theo phiên bản.

Integration seed dùng schema PostgreSQL tạm riêng trong database thử: kiểm tra nhập theo lô, rollback/thử lại, hai phiên nhập đồng thời, schema sai và khôi phục tất cả bảng/nhãn/tệp của snapshot công khai đã được phép. Không gắn storage/model volume thật. Có thể chạy riêng bằng `python scripts/test-integration.py -k shared_data`; runner vẫn áp dụng đủ migration và dọn container sau test.

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

Kiểm fresh-install bằng project/cổng/env riêng. Dùng dữ liệu giả cho thử thao tác ghi; snapshot thật đã được phép chia sẻ có thể dùng cho kiểm tra khôi phục/đọc, không thao tác trên volume nguồn. Thử boot lần hai giữ secret/tài khoản, missing-env fail-closed, login/import/upload/worker/review/monthreport thật. **Hai reader thật** chỉ xác minh chúng nhận/chạy/trả contract trên ảnh thử; không suy thành accuracy công tơ.

## Backup và CI

Verify manifest + archive safety, diễn tập restore ở resource tạm theo [backup](backup-restore.md). Không dùng backup SQL không tin cậy.

CI trên push master/PR kiểm secret, docs/bootstrap, backend, integration, frontend, AI và Compose; CodeQL workflow riêng. Kết quả phải gắn commit cụ thể. Các số test/bộ đo cũ đặt ở docs/reports, không dùng số cũ như số của HEAD.

Xem [checklist](release-checklist.md), [báo cáo ngày 13/10](reports/final-verification-2026-10-13.md).
