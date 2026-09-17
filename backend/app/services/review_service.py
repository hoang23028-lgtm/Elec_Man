from datetime import UTC, datetime
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.ai_result import AiResult
from app.models.batch import Batch
from app.models.audit_log import AuditLog
from app.models.image import ImageRecord, ImageStatus
from app.models.manual_correction import ManualCorrection
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.schemas.result import ResultRow, ReviewRequest

def list_results(db: Session, offset: int, limit: int, image_status: str | None, search: str | None) -> list[ResultRow]:
    stmt = select(ImageRecord, AiResult, MeterReading).join(AiResult, AiResult.image_id == ImageRecord.id).outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id).order_by(AiResult.created_at.desc()).offset(offset).limit(limit)
    if image_status:
        stmt = stmt.where(ImageRecord.status == image_status)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(ImageRecord.original_filename.ilike(term) | AiResult.customer_id_ai.ilike(term) | AiResult.meter_reading_ai.ilike(term))
    return [ResultRow(image_id=image.id, original_filename=image.original_filename, image_status=image.status, ai_result_id=ai.id, customer_id_ai=ai.customer_id_ai, meter_reading_ai=ai.meter_reading_ai, final_confidence=ai.final_confidence, ai_status=ai.status, review_status=reading.review_status if reading else None, final_customer_id=reading.final_customer_id if reading else None, final_meter_reading=reading.final_meter_reading if reading else None) for image, ai, reading in db.execute(stmt)]

def review_result(db: Session, image_id: UUID, payload: ReviewRequest, user: User, ip_address: str | None) -> MeterReading:
    image = db.get(ImageRecord, image_id)
    ai = db.scalar(select(AiResult).where(AiResult.image_id == image_id))
    if image is None or ai is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found.")
    if payload.action == "CONFIRM" and (not payload.final_customer_id or not payload.final_meter_reading):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Confirmed results require both final values.")
    reading = db.scalar(select(MeterReading).where(MeterReading.image_id == image_id))
    if reading is None:
        reading = MeterReading(image_id=image_id, ai_result_id=ai.id)
        db.add(reading)
        old_customer = ai.customer_id_ai
        old_meter = ai.meter_reading_ai
    else:
        old_customer = reading.final_customer_id
        old_meter = reading.final_meter_reading
    for field, old, new in (("customer_id", old_customer, payload.final_customer_id), ("meter_reading", old_meter, payload.final_meter_reading)):
        if old != new:
            db.add(ManualCorrection(image_id=image_id, ai_result_id=ai.id, field_name=field, old_value=old, new_value=new, reason=payload.reason, created_by=user.id))
    now = datetime.now(UTC)
    reading.final_customer_id = payload.final_customer_id
    reading.final_meter_reading = payload.final_meter_reading
    reading.review_status = "CONFIRMED" if payload.action == "CONFIRM" else "REJECTED"
    reading.reviewed_by = user.id
    reading.reviewed_at = now
    image.status = ImageStatus.CONFIRMED if payload.action == "CONFIRM" else ImageStatus.REJECTED
    batch = db.get(Batch, image.batch_id)
    if batch is not None:
        batch.review_count = int(db.scalar(select(func.count()).select_from(ImageRecord).where(ImageRecord.batch_id == image.batch_id, ImageRecord.status == ImageStatus.REVIEW_REQUIRED)) or 0)
        batch.ok_count = int(db.scalar(select(func.count()).select_from(ImageRecord).where(ImageRecord.batch_id == image.batch_id, ImageRecord.status == ImageStatus.CONFIRMED)) or 0)
        batch.ng_count = int(db.scalar(select(func.count()).select_from(ImageRecord).where(ImageRecord.batch_id == image.batch_id, ImageRecord.status == ImageStatus.REJECTED)) or 0)
    db.add(AuditLog(user_id=user.id, action="CONFIRM_RESULT" if payload.action == "CONFIRM" else "REJECT_RESULT", target_type="image", target_id=str(image_id), details_json={"ai_result_id": str(ai.id), "reason": payload.reason}, ip_address=ip_address))
    db.commit(); db.refresh(reading)
    return reading
