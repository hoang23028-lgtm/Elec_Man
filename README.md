# Electricity Meter AI Management System

Internal, single-administrator web system for secure batch processing and human review of electricity-meter images.

## Phase 1 status

The project foundation is in place: Next.js frontend, FastAPI backend, PostgreSQL connection layer, Alembic, separate worker process, Nginx proxy, structured logs, and health checks. Authentication, database entities, uploads, and AI inference are intentionally deferred to later phases.

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

Phase 4 provides a PostgreSQL-backed worker queue and a deliberately non-inference `MOCK` processor. See [job documentation](docs/jobs.md).

## AI pipeline

Phase 5 adds modular quality, preprocessing, detector/OCR, validation, and confidence interfaces. The current development pipeline is deliberately marked `MOCK`; see [AI pipeline documentation](docs/ai-pipeline.md).

## Training data

Approved seed labels are recorded without source images in `training/annotations.jsonl`. The first labelled sample is documented in [training guidance](docs/training.md). A single labelled image is not enough to train or validate a real recognition model.

## Review

Phase 6 separates immutable AI output from reviewed final values and records every correction; see [review documentation](docs/review.md).

## Dashboard and export

Phase 7 provides authenticated dashboard statistics and safe Excel export of confirmed final readings; see [export documentation](docs/export.md).

PostgreSQL is intentionally not published. Use an internal HTTPS endpoint in production and add HSTS only after TLS is verified. Docker Desktop must be running before building or starting the stack.
