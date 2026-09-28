import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ai_result import AiResult
from app.models.audit_log import AuditLog
from app.models.image import ImageRecord, ImageStatus
from app.models.manual_correction import ManualCorrection
from app.models.meter_reading import MeterReading
from app.models.processing_job import JobStatus, ProcessingJob
from app.models.user import User
from app.schemas.result import (
    ReadingPolygon,
    RecognitionResponse,
    RecognitionStatusResponse,
)
from app.services.job_service import refresh_batch_counters
from app.services.meter_value import normalize_meter_reading, parse_meter_value


def _bbox_dict(reading: MeterReading | None) -> dict | None:
    if (
        reading is None
        or reading.reading_bbox_x is None
        or reading.reading_bbox_y is None
        or reading.reading_bbox_width is None
        or reading.reading_bbox_height is None
    ):
        return None
    return {
        "x": reading.reading_bbox_x,
        "y": reading.reading_bbox_y,
        "width": reading.reading_bbox_width,
        "height": reading.reading_bbox_height,
    }


def queue_region_recognition(
    db: Session,
    image_id: UUID,
    polygon: ReadingPolygon,
    user: User,
    ip_address: str | None,
) -> RecognitionResponse:
    record = db.execute(
        select(ImageRecord, AiResult, MeterReading, ProcessingJob)
        .join(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .join(ProcessingJob, ProcessingJob.image_id == ImageRecord.id)
        .where(ImageRecord.id == image_id)
        .with_for_update(of=ProcessingJob)
    ).one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kết quả.")
    image, ai_result, reading, job = record
    if image.status != ImageStatus.REVIEW_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể xác định lại chỉ số của kết quả đang chờ xử lý.",
        )
    if job.status in {JobStatus.PENDING, JobStatus.PROCESSING}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ảnh đang được xử lý. Vui lòng chờ kết quả hiện tại hoàn tất.",
        )

    if reading is None:
        reading = MeterReading(image_id=image.id, ai_result_id=ai_result.id)
        db.add(reading)
    old_bbox = _bbox_dict(reading)
    old_polygon = reading.reading_polygon_json
    new_polygon = polygon.model_dump()
    bbox = polygon.bounding_box()
    new_bbox = bbox.model_dump()
    now = datetime.now(UTC)
    reading.reading_bbox_x = bbox.x
    reading.reading_bbox_y = bbox.y
    reading.reading_bbox_width = bbox.width
    reading.reading_bbox_height = bbox.height
    reading.reading_polygon_json = new_polygon
    reading.bbox_reviewed_by = user.id
    reading.bbox_reviewed_at = now
    if old_polygon != new_polygon:
        db.add(
            ManualCorrection(
                image_id=image.id,
                ai_result_id=ai_result.id,
                field_name="reading_polygon",
                old_value=json.dumps(old_polygon, ensure_ascii=False, sort_keys=True),
                new_value=json.dumps(new_polygon, ensure_ascii=False, sort_keys=True),
                reason="Khoanh vùng để xác định lại chỉ số",
                created_by=user.id,
            )
        )

    job.status = JobStatus.PENDING
    job.priority = max(job.priority, 10)
    job.attempt_count = 0
    job.max_attempts = get_settings().max_retry_count
    job.error_code = None
    job.error_message = None
    job.result_json = None
    job.input_json = {
        "reading_polygon": new_polygon,
        "reading_bbox": new_bbox,
        "source": "HUMAN_REVIEW",
        "requested_by": str(user.id),
    }
    job.started_at = None
    job.completed_at = None
    job.next_retry_at = now
    job.worker_id = None
    db.add(
        AuditLog(
            user_id=user.id,
            action="READING_REGION_RECOGNITION_QUEUED",
            target_type="image",
            target_id=str(image.id),
            details_json={
                "job_id": str(job.id),
                "original_filename": image.original_filename,
                "reading_bbox_before": old_bbox,
                "reading_bbox_after": new_bbox,
                "reading_polygon_before": old_polygon,
                "reading_polygon_after": new_polygon,
                "meter_reading_before": ai_result.meter_reading_ai,
                "new_status": "PENDING",
            },
            ip_address=ip_address,
        )
    )
    db.flush()
    refresh_batch_counters(db, image.batch_id)
    db.commit()
    return RecognitionResponse(image_id=image.id, job_id=job.id, status=job.status)


def region_recognition_status(db: Session, image_id: UUID) -> RecognitionStatusResponse:
    record = db.execute(
        select(ProcessingJob, AiResult)
        .join(AiResult, AiResult.image_id == ProcessingJob.image_id)
        .where(ProcessingJob.image_id == image_id)
    ).one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tác vụ.")
    job, ai_result = record
    result = job.result_json or {}
    return RecognitionStatusResponse(
        image_id=image_id,
        job_id=job.id,
        status=job.status,
        meter_reading_ai=(
            result.get("meter_reading_ai")
            if job.status == JobStatus.COMPLETED
            else ai_result.meter_reading_ai
        ),
        meter_confidence=(
            result.get("meter_confidence")
            if job.status == JobStatus.COMPLETED
            else ai_result.meter_confidence
        ),
        error_message=job.error_message if job.status == JobStatus.FAILED else None,
    )


def save_training_label(
    db: Session,
    image_id: UUID,
    meter_reading: str,
    polygon: ReadingPolygon,
    user: User,
    ip_address: str | None,
) -> MeterReading:
    record = db.execute(
        select(ImageRecord, AiResult, MeterReading)
        .join(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .where(ImageRecord.id == image_id)
        .with_for_update(of=ImageRecord)
    ).one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kết quả.")
    image, ai_result, reading = record
    if image.status != ImageStatus.REVIEW_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể lưu nhãn cho kết quả đang chờ xử lý.",
        )
    normalized = normalize_meter_reading(meter_reading)
    if normalized is None or not 4 <= len(normalized) <= 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nhãn chỉ số phải gồm từ 4 đến 8 chữ số nguyên.",
        )
    if reading is None:
        reading = MeterReading(image_id=image.id, ai_result_id=ai_result.id)
        db.add(reading)
    old_meter = reading.final_meter_reading
    old_polygon = reading.reading_polygon_json
    new_polygon = polygon.model_dump()
    bbox = polygon.bounding_box()
    now = datetime.now(UTC)
    reading.final_meter_reading = normalized
    reading.reading_value = parse_meter_value(normalized)
    reading.reading_bbox_x = bbox.x
    reading.reading_bbox_y = bbox.y
    reading.reading_bbox_width = bbox.width
    reading.reading_bbox_height = bbox.height
    reading.reading_polygon_json = new_polygon
    reading.bbox_reviewed_by = user.id
    reading.bbox_reviewed_at = now
    reading.review_status = "LABELED"
    reading.reviewed_by = user.id
    reading.reviewed_at = now
    for field_name, old_value, new_value in (
        ("meter_reading", old_meter, normalized),
        (
            "reading_polygon",
            json.dumps(old_polygon, ensure_ascii=False, sort_keys=True),
            json.dumps(new_polygon, ensure_ascii=False, sort_keys=True),
        ),
    ):
        if old_value != new_value:
            db.add(
                ManualCorrection(
                    image_id=image.id,
                    ai_result_id=ai_result.id,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                    reason="Nhãn huấn luyện do người dùng xác nhận",
                    created_by=user.id,
                )
            )
    db.add(
        AuditLog(
            user_id=user.id,
            action="SAVE_TRAINING_LABEL",
            target_type="image",
            target_id=str(image.id),
            details_json={
                "original_filename": image.original_filename,
                "meter_reading_before": old_meter,
                "meter_reading_after": normalized,
                "reading_polygon_before": old_polygon,
                "reading_polygon_after": new_polygon,
                "new_status": "LABELED",
            },
            ip_address=ip_address,
        )
    )
    db.commit()
    db.refresh(reading)
    return reading
