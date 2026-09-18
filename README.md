# Electricity Meter AI Management System

Internal, single-administrator web system for secure batch processing and human review of electricity-meter images.

## Current status

The runnable prototype includes the Next.js frontend, FastAPI backend, PostgreSQL, Alembic migrations, authenticated local image storage, a PostgreSQL job queue, separate OCR worker, review workflow, dashboard, Excel export, Nginx proxy, structured logs, and health checks.

## Start

Copy `.env.example` to `.env`, replace `POSTGRES_PASSWORD` and the password in `DATABASE_URL` with the same strong secret, then run:

```powershell
docker compose up --build
```

Open `http://localhost/`. Backend liveness is `/api/v1/health/live`; readiness is `/api/v1/health/ready`.

## Migrations and testing

Alembic wiring is ready; schema migrations begin in Phase 2. Run migrations with `docker compose exec backend alembic upgrade head`. Python tests require a Python 3.12+ environment with backend development dependencies, then run `pytest backend/tests`.

## Administrator initialization

After applying migrations, set `ADMIN_INITIAL_PASSWORD` temporarily and run `python -m app.scripts.init_admin --username <username>` inside the backend container. See [security documentation](docs/security.md). There is intentionally no registration endpoint or default administrator password.

## Uploads

Phase 3 provides authenticated, one-image-per-request batch uploads. Originals are stored locally with UUID names and are available only through authenticated previews. See [storage documentation](docs/storage.md).

## Processing jobs

The PostgreSQL-backed worker queue safely processes images outside HTTP requests. See [job documentation](docs/jobs.md).

## AI pipeline

The current development model is `meter-ocr-baseline-v1`, built from OpenCV, pretrained RapidOCR ONNX models, and a Tesseract fallback. It always requires human review and must not be described as a production-trained model; see [AI pipeline documentation](docs/ai-pipeline.md).

## Training data

Approved seed labels are recorded without source images in `training/annotations.jsonl`. The first labelled sample is documented in [training guidance](docs/training.md). A single labelled image is not enough to train or validate a real recognition model.

## Review

Phase 6 separates immutable AI output from reviewed final values and records every correction; see [review documentation](docs/review.md).

## Dashboard and export

Phase 7 provides authenticated dashboard statistics and safe Excel export of confirmed final readings; see [export documentation](docs/export.md).

## Administration and backup

The dashboard includes audited system settings, a checksum-verified model registry, operational AI evaluation, and audit history. See [administration](docs/administration.md) and [backup/restore](docs/backup-restore.md).

PostgreSQL is intentionally not published. Use an internal HTTPS endpoint in production and add HSTS only after TLS is verified. Docker Desktop must be running before building or starting the stack.
