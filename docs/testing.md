# Kiểm thử

Dự án gồm kiểm thử backend, pipeline AI, kiểm tra tĩnh frontend và kiểm thử khói cho bản triển khai Docker.

## Backend

Sau khi cài dependency phát triển của backend bằng Python 3.12 trở lên:

```powershell
python -m pytest backend/tests
python -m ruff check backend/app backend/tests backend/alembic ai
python -m ruff format --check backend/app backend/tests backend/alembic ai
```

## Pipeline AI

Các kiểm thử AI cần OpenCV và RapidOCR. Chạy bằng image worker để dùng đúng dependency production:

```powershell
docker run --rm --volume "${PWD}:/workspace" --workdir /workspace elec_man-worker `
  python -m pytest -p no:cacheprovider ai/tests
```

## Frontend

```powershell
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm audit --prefix frontend
```

## Bản triển khai

Sau khi dựng Docker, xác nhận trang chủ và API `/api/v1/health/ready` trả về HTTP 200, đồng thời kiểm tra các container backend, frontend, worker và trainer đang hoạt động bình thường.
