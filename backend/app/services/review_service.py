from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_result import AiResult
from app.models.audit_log import AuditLog
from app.models.image import ImageRecord, ImageStatus
from app.models.manual_correction import ManualCorrection
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.schemas.result import ResultRow, ReviewRequest
from app.services.job_service import refresh_batch_counters


def list_results(
    db: Session,
    offset: int,
    limit: int,
    image_status: str | None,
    search: str | None,
) -> list[ResultRow]:
    statement = (
        select(ImageRecord, AiResult, MeterReading)
        .join(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .order_by(AiResult.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if image_status:
        statement = statement.where(ImageRecord.status == image_status)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            ImageRecord.original_filename.ilike(term)
            | AiResult.customer_id_ai.ilike(term)
            | AiResult.meter_reading_ai.ilike(term)
            | MeterReading.final_customer_id.ilike(term)
            | MeterReading.final_meter_reading.ilike(term)
        )
    return [
        ResultRow(
            image_id=image.id,
            original_filename=image.original_filename,
            image_status=image.status,
            ai_result_id=ai_result.id,
            customer_id_ai=ai_result.customer_id_ai,
            meter_reading_ai=ai_result.meter_reading_ai,
            final_confidence=ai_result.final_confidence,
            ai_status=ai_result.status,
            review_status=reading.review_status if reading else None,
            auto_confirmed=bool(
                reading
                and reading.review_status == "CONFIRMED"
                and reading.reviewed_by is None
            ),
            final_customer_id=reading.final_customer_id if reading else None,
            final_meter_reading=reading.final_meter_reading if reading else None,
        )
        for image, ai_result, reading in db.execute(statement)
    ]


def review_result(
    db: Session,
    image_id: UUID,
    payload: ReviewRequest,
    user: User,
    ip_address: str | None,
) -> MeterReading:
    image = db.get(ImageRecord, image_id)
    ai_result = db.scalar(select(AiResult).where(AiResult.image_id == image_id))
    if image is None or ai_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kết quả.")
    if payload.action == "CONFIRM" and (
        not payload.final_customer_id or not payload.final_meter_reading
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Kết quả xác nhận phải có đủ hai giá trị cuối cùng.",
        )

    reading = db.scalar(select(MeterReading).where(MeterReading.image_id == image_id))
    if reading is None:
        reading = MeterReading(image_id=image_id, ai_result_id=ai_result.id)
        db.add(reading)
        old_customer = ai_result.customer_id_ai
        old_meter = ai_result.meter_reading_ai
    else:
        old_customer = reading.final_customer_id
        old_meter = reading.final_meter_reading

    was_confirmed = bool(reading and reading.review_status == "CONFIRMED")
    corrections = (
        ("customer_id", old_customer, payload.final_customer_id),
        ("meter_reading", old_meter, payload.final_meter_reading),
    )
    correction_count = 0
    for field, old, new in corrections:
        if old != new:
            correction_count += 1
            db.add(
                ManualCorrection(
                    image_id=image_id,
                    ai_result_id=ai_result.id,
                    field_name=field,
                    old_value=old,
                    new_value=new,
                    reason=payload.reason,
                    created_by=user.id,
                )
            )

    reading.final_customer_id = payload.final_customer_id
    reading.final_meter_reading = payload.final_meter_reading
    reading.review_status = "CONFIRMED" if payload.action == "CONFIRM" else "REJECTED"
    reading.reviewed_by = user.id
    reading.reviewed_at = datetime.now(UTC)
    image.status = ImageStatus.CONFIRMED if payload.action == "CONFIRM" else ImageStatus.REJECTED
    db.flush()
    refresh_batch_counters(db, image.batch_id)
    db.add(
        AuditLog(
            user_id=user.id,
            action=(
                "UPDATE_CONFIRMED_RESULT"
                if payload.action == "CONFIRM" and was_confirmed
                else "CONFIRM_RESULT"
                if payload.action == "CONFIRM"
                else "REJECT_RESULT"
            ),
            target_type="image",
            target_id=str(image_id),
            details_json={
                "ai_result_id": str(ai_result.id),
                "reason": payload.reason,
                "correction_count": correction_count,
            },
            ip_address=ip_address,
        )
    )
    db.commit()
    return reading
