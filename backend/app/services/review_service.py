from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_result import AiResult
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.image import ImageRecord, ImageStatus
from app.models.manual_correction import ManualCorrection
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.schemas.result import ResultRow, ReviewRequest
from app.services.customer_service import apply_customer_match, find_customer
from app.services.job_service import refresh_batch_counters
from app.services.meter_value import normalize_meter_reading, parse_meter_value
from app.services.reviewed_image_service import archive_reviewed_image, remove_reviewed_image


def _apply_result_filters(statement, image_status: str | None, search: str | None):
    if image_status:
        statement = statement.where(ImageRecord.status == image_status)
    if not search:
        return statement
    term = f"%{search.strip()}%"
    return statement.where(
        ImageRecord.original_filename.ilike(term)
        | AiResult.customer_id_ai.ilike(term)
        | AiResult.meter_reading_ai.ilike(term)
        | MeterReading.final_customer_id.ilike(term)
        | MeterReading.final_meter_reading.ilike(term)
        | Customer.full_name.ilike(term)
    )


def list_results(
    db: Session,
    offset: int,
    limit: int,
    image_status: str | None,
    search: str | None,
) -> tuple[list[ResultRow], int]:
    statement = (
        select(
            ImageRecord,
            AiResult,
            MeterReading,
            Customer,
            func.count(ImageRecord.id).over().label("total_count"),
        )
        .join(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .outerjoin(Customer, Customer.id == MeterReading.matched_customer_id)
        .order_by(AiResult.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    statement = _apply_result_filters(statement, image_status, search)
    rows = db.execute(statement).all()
    items = [
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
                reading and reading.review_status == "CONFIRMED" and reading.reviewed_by is None
            ),
            final_customer_id=reading.final_customer_id if reading else None,
            final_meter_reading=reading.final_meter_reading if reading else None,
            customer_match_status=(reading.customer_match_status if reading else "NOT_CHECKED"),
            matched_customer_name=customer.full_name if customer else None,
            matched_meter_serial=customer.meter_serial if customer else None,
        )
        for image, ai_result, reading, customer, _ in rows
    ]
    total = int(rows[0].total_count) if rows else 0
    if not rows and offset:
        count_statement = (
            select(func.count(ImageRecord.id))
            .join(AiResult, AiResult.image_id == ImageRecord.id)
            .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
            .outerjoin(Customer, Customer.id == MeterReading.matched_customer_id)
        )
        count_statement = _apply_result_filters(count_statement, image_status, search)
        total = int(db.scalar(count_statement) or 0)
    return items, total


def review_result(
    db: Session,
    image_id: UUID,
    payload: ReviewRequest,
    user: User,
    ip_address: str | None,
) -> MeterReading:
    record = db.execute(
        select(ImageRecord, AiResult, MeterReading)
        .join(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .where(ImageRecord.id == image_id)
    ).one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kết quả.")
    image, ai_result, reading = record
    if payload.action == "CONFIRM" and (
        not payload.final_customer_id or not payload.final_meter_reading
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Kết quả xác nhận phải có đủ hai giá trị cuối cùng.",
        )
    normalized_meter = normalize_meter_reading(payload.final_meter_reading)
    reading_value = parse_meter_value(normalized_meter)
    if payload.action == "CONFIRM" and normalized_meter is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Số điện phải là số nguyên không âm; phần sau dấu phẩy sẽ không được lấy.",
        )
    final_meter = normalized_meter or payload.final_meter_reading
    matched_customer = find_customer(db, payload.final_customer_id)
    final_customer = (
        matched_customer.customer_code if matched_customer else payload.final_customer_id
    )

    previous_review_status = reading.review_status if reading else "UNREVIEWED"
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
        ("customer_id", old_customer, final_customer),
        ("meter_reading", old_meter, final_meter),
    )
    correction_count = 0
    changed_fields: list[str] = []
    for field, old, new in corrections:
        if old != new:
            correction_count += 1
            changed_fields.append(field)
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

    reading.final_customer_id = final_customer
    reading.final_meter_reading = final_meter
    reading.reading_value = reading_value if payload.action == "CONFIRM" else None
    if payload.action == "CONFIRM":
        apply_customer_match(reading, matched_customer)
    else:
        reading.matched_customer_id = None
        reading.customer_match_status = "NOT_CHECKED"
    reading.review_status = "CONFIRMED" if payload.action == "CONFIRM" else "REJECTED"
    reading.reviewed_by = user.id
    reading.reviewed_at = datetime.now(UTC)
    image.status = ImageStatus.CONFIRMED if payload.action == "CONFIRM" else ImageStatus.REJECTED
    reviewed_image_path = None
    removed_reviewed_image_path = None
    if payload.action == "CONFIRM":
        reviewed_image_path = archive_reviewed_image(
            image, reading.final_customer_id, reading.reviewed_at
        )
    else:
        removed_reviewed_image_path = remove_reviewed_image(image)
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
                "batch_id": str(image.batch_id),
                "original_filename": image.original_filename,
                "reason": payload.reason,
                "correction_count": correction_count,
                "changed_fields": changed_fields,
                "review_action": payload.action,
                "previous_status": previous_review_status,
                "new_status": reading.review_status,
                "ai_customer_id": ai_result.customer_id_ai,
                "ai_meter_reading": ai_result.meter_reading_ai,
                "customer_id_before": old_customer,
                "customer_id_after": reading.final_customer_id,
                "meter_reading_before": old_meter,
                "meter_reading_after": reading.final_meter_reading,
                "customer_match_status": reading.customer_match_status,
                "matched_customer_id": (
                    str(reading.matched_customer_id) if reading.matched_customer_id else None
                ),
                "reviewed_image_path": reviewed_image_path,
                "removed_reviewed_image_path": removed_reviewed_image_path,
            },
            ip_address=ip_address,
        )
    )
    db.commit()
    return reading
