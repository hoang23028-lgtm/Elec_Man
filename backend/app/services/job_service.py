from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.batch import Batch, BatchStatus
from app.models.image import ImageRecord, ImageStatus
from app.models.processing_job import JobStatus, ProcessingJob
from app.models.user import User


def queue_batch(db: Session, batch_id: UUID, user: User, ip_address: str | None) -> Batch:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    if batch.status not in {BatchStatus.UPLOADING, BatchStatus.READY}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Batch cannot be queued in its current state.")
    image_ids = list(db.scalars(select(ImageRecord.id).where(ImageRecord.batch_id == batch_id)))
    if not image_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Batch has no uploaded images.")
    existing = db.scalar(select(func.count()).select_from(ProcessingJob).join(ImageRecord).where(ImageRecord.batch_id == batch_id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Batch already has processing jobs.")
    now = datetime.now(UTC)
    settings = get_settings()
    db.add_all([ProcessingJob(image_id=image_id, status=JobStatus.PENDING, max_attempts=settings.max_retry_count, created_at=now, next_retry_at=now) for image_id in image_ids])
    db.execute(update(ImageRecord).where(ImageRecord.batch_id == batch_id).values(status=ImageStatus.QUEUED))
    batch.status = BatchStatus.QUEUED
    db.add(AuditLog(user_id=user.id, action="START_BATCH", target_type="batch", target_id=str(batch.id), details_json={"job_count": len(image_ids), "processor": "OCR_BASELINE"}, ip_address=ip_address))
    db.commit()
    db.refresh(batch)
    return batch


def recover_stuck_jobs(db: Session) -> int:
    timeout = datetime.now(UTC) - timedelta(seconds=get_settings().job_stuck_timeout_seconds)
    stuck_jobs = list(db.scalars(select(ProcessingJob).where(ProcessingJob.status == JobStatus.PROCESSING, ProcessingJob.started_at < timeout).with_for_update(skip_locked=True)))
    now = datetime.now(UTC)
    for job in stuck_jobs:
        job.error_code = "WORKER_RECOVERY"
        job.error_message = "Recovered after worker heartbeat timeout."
        job.worker_id = None
        job.started_at = None
        if job.attempt_count >= job.max_attempts:
            job.status = JobStatus.FAILED
            job.completed_at = now
        else:
            job.status = JobStatus.PENDING
            job.next_retry_at = now
    if stuck_jobs:
        db.commit()
    return len(stuck_jobs)


def claim_next_job(db: Session, worker_id: str) -> ProcessingJob | None:
    now = datetime.now(UTC)
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.status == JobStatus.PENDING, ProcessingJob.next_retry_at <= now).order_by(ProcessingJob.priority.desc(), ProcessingJob.created_at).with_for_update(skip_locked=True).limit(1))
    if job is None:
        db.commit()
        return None
    job.status = JobStatus.PROCESSING
    job.attempt_count += 1
    job.started_at = now
    job.worker_id = worker_id
    job.error_code = None
    job.error_message = None
    db.commit()
    db.refresh(job)
    return job


def _refresh_batch_status(db: Session, image_id: UUID) -> None:
    batch_id = db.scalar(select(ImageRecord.batch_id).where(ImageRecord.id == image_id))
    if batch_id is None:
        return
    pending, processing, completed, failed = db.execute(select(func.count().filter(ProcessingJob.status == JobStatus.PENDING), func.count().filter(ProcessingJob.status == JobStatus.PROCESSING), func.count().filter(ProcessingJob.status == JobStatus.COMPLETED), func.count().filter(ProcessingJob.status == JobStatus.FAILED)).join(ImageRecord).where(ImageRecord.batch_id == batch_id)).one()
    batch = db.get(Batch, batch_id)
    if batch is None:
        return
    batch.processed_images = int(completed) + int(failed)
    batch.failed_count = int(failed)
    batch.review_count = int(db.scalar(select(func.count()).select_from(ImageRecord).where(ImageRecord.batch_id == batch_id, ImageRecord.status == ImageStatus.REVIEW_REQUIRED)) or 0)
    batch.ok_count = int(db.scalar(select(func.count()).select_from(ImageRecord).where(ImageRecord.batch_id == batch_id, ImageRecord.status == ImageStatus.CONFIRMED)) or 0)
    batch.ng_count = int(db.scalar(select(func.count()).select_from(ImageRecord).where(ImageRecord.batch_id == batch_id, ImageRecord.status == ImageStatus.REJECTED)) or 0)
    if pending or processing:
        batch.status = BatchStatus.PROCESSING
    elif failed:
        batch.status = BatchStatus.PARTIAL_FAILED
        batch.completed_at = datetime.now(UTC)
    else:
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = datetime.now(UTC)


def mark_job_completed(db: Session, job_id: UUID, result_json: dict) -> None:
    job = db.get(ProcessingJob, job_id)
    if job is None or job.status != JobStatus.PROCESSING:
        return
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.now(UTC)
    job.result_json = result_json
    image_status = ImageStatus.REVIEW_REQUIRED if result_json.get("status") == "REVIEW" else ImageStatus.AI_COMPLETED
    db.execute(update(ImageRecord).where(ImageRecord.id == job.image_id).values(status=image_status))
    db.flush()
    _refresh_batch_status(db, job.image_id)
    db.commit()


def mark_job_failure(db: Session, job_id: UUID, error_code: str, error_message: str) -> None:
    job = db.get(ProcessingJob, job_id)
    if job is None or job.status != JobStatus.PROCESSING:
        return
    now = datetime.now(UTC)
    job.error_code = error_code[:64]
    job.error_message = error_message[:2000]
    if job.attempt_count >= job.max_attempts:
        job.status = JobStatus.FAILED
        job.completed_at = now
        db.execute(update(ImageRecord).where(ImageRecord.id == job.image_id).values(status=ImageStatus.FAILED))
    else:
        job.status = JobStatus.PENDING
        job.next_retry_at = now + timedelta(seconds=min(60, 2 ** job.attempt_count))
        job.worker_id = None
        job.started_at = None
    db.flush()
    _refresh_batch_status(db, job.image_id)
    db.commit()
