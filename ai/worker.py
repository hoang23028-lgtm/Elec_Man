"""Database-backed Phase 4 worker with explicitly mock processing."""
import logging
import signal
import time
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.database import SessionLocal
from app.models.image import ImageRecord
from app.services.job_service import claim_next_job, mark_job_completed, mark_job_failure, recover_stuck_jobs
from ai.pipeline.pipeline import DevelopmentPipeline
from app.services.ai_result_service import store_immutable_ai_result
running = True
def _stop(_: int, __: object) -> None:
    global running
    running = False
def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)
    worker_id = f"worker-{uuid4().hex[:12]}"
    processor = DevelopmentPipeline()
    logger.info("worker_started", extra={"event": "worker_started", "worker_id": worker_id, "processor": processor.name})
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while running:
        try:
            with SessionLocal() as db:
                recover_stuck_jobs(db)
                job = claim_next_job(db, worker_id)
                if job is None:
                    time.sleep(get_settings().worker_poll_interval_seconds)
                    continue
                try:
                    image = db.get(ImageRecord, job.image_id)
                    if image is None:
                        raise FileNotFoundError("Image metadata is unavailable.")
                    image_path = Path(get_settings().storage_root) / image.relative_path
                    result = processor.process(image_path)
                    store_immutable_ai_result(db, job.image_id, result)
                    mark_job_completed(db, job.id, result)
                    logger.info("job_completed", extra={"event": "job_completed", "job_id": str(job.id), "processor": processor.name})
                except Exception as exc:
                    mark_job_failure(db, job.id, "MOCK_PROCESSING_ERROR", str(exc))
                    logger.warning("job_failed", extra={"event": "job_failed", "job_id": str(job.id)})
        except Exception:
            logger.exception("worker_iteration_failed", extra={"event": "worker_iteration_failed"})
            time.sleep(get_settings().worker_poll_interval_seconds)
    logger.info("worker_stopped", extra={"event": "worker_stopped"})
if __name__ == "__main__":
    main()
