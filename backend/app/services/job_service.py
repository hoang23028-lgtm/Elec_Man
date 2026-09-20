from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai_result import AiResult
from app.models.audit_log import AuditLog
from app.models.batch import Batch, BatchStatus
from app.models.image import ImageRecord, ImageStatus
from app.models.meter_reading import MeterReading
from app.models.processing_job import JobStatus, ProcessingJob
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.services.meter_value import normalize_meter_reading, parse_meter_value

DEFAULT_AUTO_CONFIRM_THRESHOLD = 0.9


def should_auto_confirm(result_json: dict, threshold: float) -> bool:
    """Only complete, high-confidence results may bypass human review."""
    try:
        confidence = float(result_json.get("final_confidence", 0))
    except (TypeError, ValueError):
        return False
    return bool(
        confidence > threshold
        and result_json.get("customer_id_ai")
        and result_json.get("meter_reading_ai")
        and parse_meter_value(result_json.get("meter_reading_ai")) is not None
    )


def get_auto_confirm_threshold(db: Session) -> float:
    setting = db.get(SystemSetting, "confidence_ok_threshold")
    if setting is None:
        return DEFAULT_AUTO_CONFIRM_THRESHOLD
    try:
        return float(setting.value_json)
    except (TypeError, ValueError):
        return DEFAULT_AUTO_CONFIRM_THRESHOLD


def queue_batch(db: Session, batch_id: UUID, user: User, ip_address: str | None) -> Batch:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lô dữ liệu."
        )
    if batch.status not in {BatchStatus.UPLOADING, BatchStatus.READY}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể đưa lô dữ liệu vào hàng đợi ở trạng thái hiện tại.",
        )
    image_ids = list(db.scalars(select(ImageRecord.id).where(ImageRecord.batch_id == batch_id)))
    if not image_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Lô dữ liệu chưa có ảnh được tải lên.",
        )
    existing = db.scalar(
        select(ProcessingJob.id).join(ImageRecord).where(ImageRecord.batch_id == batch_id).limit(1)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lô dữ liệu đã có tác vụ xử lý.",
        )
    now = datetime.now(UTC)
    settings = get_settings()
    previous_status = batch.status
    db.add_all(
        [
            ProcessingJob(
                image_id=image_id,
                status=JobStatus.PENDING,
                max_attempts=settings.max_retry_count,
                created_at=now,
                next_retry_at=now,
            )
            for image_id in image_ids
        ]
    )
    db.execute(
        update(ImageRecord)
        .where(ImageRecord.batch_id == batch_id)
        .values(status=ImageStatus.QUEUED)
    )
    batch.status = BatchStatus.QUEUED
    db.add(
        AuditLog(
            user_id=user.id,
            action="START_BATCH",
            target_type="batch",
            target_id=str(batch.id),
            details_json={
                "batch_code": batch.batch_code,
                "job_count": len(image_ids),
                "processor": "OCR_BASELINE",
                "max_attempts": settings.max_retry_count,
                "previous_status": previous_status,
                "new_status": BatchStatus.QUEUED,
            },
            ip_address=ip_address,
        )
    )
    db.commit()
    db.refresh(batch)
    return batch


def recover_stuck_jobs(db: Session) -> int:
    timeout = datetime.now(UTC) - timedelta(seconds=get_settings().job_stuck_timeout_seconds)
    stuck_jobs = list(
        db.scalars(
            select(ProcessingJob)
            .where(
                ProcessingJob.status == JobStatus.PROCESSING,
                ProcessingJob.started_at < timeout,
            )
            .with_for_update(skip_locked=True)
        )
    )
    now = datetime.now(UTC)
    affected_batches: set[UUID] = set()
    for job in stuck_jobs:
        job.error_code = "WORKER_RECOVERY"
        job.error_message = "Đã khôi phục sau khi tiến trình xử lý mất tín hiệu quá thời hạn."
        job.worker_id = None
        job.started_at = None
        if job.attempt_count >= job.max_attempts:
            job.status = JobStatus.FAILED
            job.completed_at = now
            image = db.get(ImageRecord, job.image_id)
            if image is not None:
                image.status = ImageStatus.FAILED
                affected_batches.add(image.batch_id)
        else:
            job.status = JobStatus.PENDING
            job.next_retry_at = now
    if stuck_jobs:
        db.flush()
        for batch_id in affected_batches:
            refresh_batch_counters(db, batch_id)
        db.commit()
    return len(stuck_jobs)


def claim_next_job(db: Session, worker_id: str) -> ProcessingJob | None:
    now = datetime.now(UTC)
    job = db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.status == JobStatus.PENDING,
            ProcessingJob.next_retry_at <= now,
        )
        .order_by(ProcessingJob.priority.desc(), ProcessingJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        db.rollback()
        return None
    job.status = JobStatus.PROCESSING
    job.attempt_count += 1
    job.started_at = now
    job.worker_id = worker_id
    job.error_code = None
    job.error_message = None
    db.commit()
    return job


def refresh_batch_counters(db: Session, batch_id: UUID) -> None:
    """Refresh all batch counters with one aggregate query."""
    pending, processing, completed, failed, review, confirmed, rejected = db.execute(
        select(
            func.count(ProcessingJob.id).filter(ProcessingJob.status == JobStatus.PENDING),
            func.count(ProcessingJob.id).filter(ProcessingJob.status == JobStatus.PROCESSING),
            func.count(ProcessingJob.id).filter(ProcessingJob.status == JobStatus.COMPLETED),
            func.count(ProcessingJob.id).filter(ProcessingJob.status == JobStatus.FAILED),
            func.count(ImageRecord.id).filter(ImageRecord.status == ImageStatus.REVIEW_REQUIRED),
            func.count(ImageRecord.id).filter(ImageRecord.status == ImageStatus.CONFIRMED),
            func.count(ImageRecord.id).filter(ImageRecord.status == ImageStatus.REJECTED),
        )
        .select_from(ImageRecord)
        .outerjoin(ProcessingJob, ProcessingJob.image_id == ImageRecord.id)
        .where(ImageRecord.batch_id == batch_id)
    ).one()
    batch = db.get(Batch, batch_id)
    if batch is None:
        return
    batch.processed_images = int(completed) + int(failed)
    batch.failed_count = int(failed)
    batch.review_count = int(review)
    batch.ok_count = int(confirmed)
    batch.ng_count = int(rejected)
    if pending or processing:
        batch.status = BatchStatus.PROCESSING
    elif failed:
        batch.status = BatchStatus.PARTIAL_FAILED
        batch.completed_at = datetime.now(UTC)
    else:
        batch.status = BatchStatus.COMPLETED
        batch.completed_at = datetime.now(UTC)


def mark_job_completed(db: Session, job_id: UUID, result_json: dict) -> None:
    record = db.execute(
        select(ProcessingJob, ImageRecord)
        .join(ImageRecord, ImageRecord.id == ProcessingJob.image_id)
        .where(ProcessingJob.id == job_id)
    ).one_or_none()
    if record is None or record[0].status != JobStatus.PROCESSING:
        return
    job, image = record
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.now(UTC)
    job.result_json = result_json
    threshold = get_auto_confirm_threshold(db)
    auto_confirmed = should_auto_confirm(result_json, threshold)
    if auto_confirmed:
        image.status = ImageStatus.CONFIRMED
        result_record = db.execute(
            select(AiResult, MeterReading)
            .outerjoin(MeterReading, MeterReading.image_id == AiResult.image_id)
            .where(AiResult.image_id == image.id)
        ).one_or_none()
        ai_result = result_record[0] if result_record else None
        if ai_result is None:
            auto_confirmed = False
            image.status = ImageStatus.REVIEW_REQUIRED
        else:
            reading = result_record[1]
            if reading is None:
                reading = MeterReading(image_id=image.id, ai_result_id=ai_result.id)
                db.add(reading)
            meter_reading = normalize_meter_reading(result_json["meter_reading_ai"])
            reading.final_customer_id = result_json["customer_id_ai"]
            reading.final_meter_reading = meter_reading
            reading.reading_value = parse_meter_value(meter_reading)
            reading.review_status = "CONFIRMED"
            reading.reviewed_by = None
            reading.reviewed_at = datetime.now(UTC)
            db.add(
                AuditLog(
                    user_id=None,
                    action="AUTO_CONFIRM_RESULT",
                    target_type="image",
                    target_id=str(image.id),
                    details_json={
                        "ai_result_id": str(ai_result.id),
                        "confidence": result_json["final_confidence"],
                        "threshold": threshold,
                        "customer_id": reading.final_customer_id,
                        "meter_reading": reading.final_meter_reading,
                        "model_version": result_json.get("model_version"),
                    },
                    ip_address=None,
                )
            )
    else:
        image.status = ImageStatus.REVIEW_REQUIRED
    db.add(
        AuditLog(
            user_id=None,
            action="PROCESSING_COMPLETED",
            target_type="image",
            target_id=str(image.id),
            details_json={
                "job_id": str(job.id),
                "batch_id": str(image.batch_id),
                "original_filename": image.original_filename,
                "processor": result_json.get("processor"),
                "model_version": result_json.get("model_version"),
                "confidence": result_json.get("final_confidence"),
                "processing_time_ms": result_json.get("processing_time_ms"),
                "auto_confirmed": auto_confirmed,
                "new_status": image.status,
            },
            ip_address=None,
        )
    )
    db.flush()
    refresh_batch_counters(db, image.batch_id)
    db.commit()


def mark_job_failure(db: Session, job_id: UUID, error_code: str, error_message: str) -> None:
    record = db.execute(
        select(ProcessingJob, ImageRecord)
        .join(ImageRecord, ImageRecord.id == ProcessingJob.image_id)
        .where(ProcessingJob.id == job_id)
    ).one_or_none()
    if record is None or record[0].status != JobStatus.PROCESSING:
        return
    job, image = record
    now = datetime.now(UTC)
    job.error_code = error_code[:64]
    job.error_message = error_message[:2000]
    if job.attempt_count >= job.max_attempts:
        job.status = JobStatus.FAILED
        job.completed_at = now
        image.status = ImageStatus.FAILED
        audit_action = "PROCESSING_FAILED"
    else:
        job.status = JobStatus.PENDING
        job.next_retry_at = now + timedelta(seconds=min(60, 2**job.attempt_count))
        job.worker_id = None
        job.started_at = None
        audit_action = "PROCESSING_RETRY_SCHEDULED"
    db.add(
        AuditLog(
            user_id=None,
            action=audit_action,
            target_type="image",
            target_id=str(image.id),
            details_json={
                "job_id": str(job.id),
                "batch_id": str(image.batch_id),
                "original_filename": image.original_filename,
                "error_code": job.error_code,
                "error_message": job.error_message,
                "attempt_count": job.attempt_count,
                "max_attempts": job.max_attempts,
                "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
                "new_status": job.status,
            },
            ip_address=None,
        )
    )
    db.flush()
    refresh_batch_counters(db, image.batch_id)
    db.commit()
