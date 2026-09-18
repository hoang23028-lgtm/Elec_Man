"""Database-backed worker for the human-reviewed OCR baseline."""

import logging
import signal
import time
from pathlib import Path
from uuid import UUID, uuid4

from ai.pipeline.pipeline import DevelopmentPipeline
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.image import ImageRecord
from app.services.ai_result_service import store_immutable_ai_result
from app.services.job_service import (
    claim_next_job,
    mark_job_completed,
    mark_job_failure,
    recover_stuck_jobs,
)

running = True


def _stop(_: int, __: object) -> None:
    global running
    running = False


def _claim(worker_id: str, recover: bool) -> tuple[UUID, UUID, Path] | None:
    """Claim work without keeping a database connection open during OCR."""
    with SessionLocal() as db:
        if recover:
            recover_stuck_jobs(db)
        job = claim_next_job(db, worker_id)
        if job is None:
            return None
        image = db.get(ImageRecord, job.image_id)
        if image is None:
            return job.id, job.image_id, Path("")
        return job.id, job.image_id, get_settings().storage_root / image.relative_path


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()
    worker_id = f"worker-{uuid4().hex[:12]}"
    processor = DevelopmentPipeline()
    poll_interval = settings.worker_poll_interval_seconds
    recovery_interval = max(60.0, min(settings.job_stuck_timeout_seconds / 2, 300.0))
    next_recovery_at = 0.0

    logger.info(
        "worker_started",
        extra={
            "event": "worker_started",
            "worker_id": worker_id,
            "processor": processor.name,
        },
    )
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while running:
        job_info: tuple[UUID, UUID, Path] | None = None
        try:
            monotonic_now = time.monotonic()
            should_recover = monotonic_now >= next_recovery_at
            job_info = _claim(worker_id, should_recover)
            if should_recover:
                next_recovery_at = monotonic_now + recovery_interval
            if job_info is None:
                time.sleep(poll_interval)
                continue

            job_id, image_id, image_path = job_info
            if not image_path.is_file():
                raise FileNotFoundError("Image file is unavailable.")
            result = processor.process(image_path)
            with SessionLocal() as db:
                store_immutable_ai_result(db, image_id, result)
                mark_job_completed(db, job_id, result)
            logger.info(
                "job_completed",
                extra={
                    "event": "job_completed",
                    "job_id": str(job_id),
                    "processor": processor.name,
                },
            )
        except Exception as exc:
            if job_info is not None:
                job_id = job_info[0]
                with SessionLocal() as db:
                    mark_job_failure(db, job_id, "OCR_PROCESSING_ERROR", str(exc))
                logger.warning(
                    "job_failed",
                    extra={"event": "job_failed", "job_id": str(job_id)},
                )
            else:
                logger.exception(
                    "worker_iteration_failed",
                    extra={"event": "worker_iteration_failed"},
                )
                time.sleep(poll_interval)

    logger.info("worker_stopped", extra={"event": "worker_stopped"})


if __name__ == "__main__":
    main()
