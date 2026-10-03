import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_result import AiResult
from app.models.audit_log import AuditLog
from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.models.customer import Customer
from app.models.image import ImageRecord, ImageStatus
from app.models.manual_correction import ManualCorrection
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.schemas.result import (
    ReadingBoundingBox,
    ReadingPolygon,
    ResultRow,
    ResultStatusCounts,
    ReviewRequest,
)
from app.services.confirmed_reading_service import (
    remove_confirmed_monthly_reading,
    save_confirmed_monthly_reading,
)
from app.services.customer_service import apply_customer_match, find_customer
from app.services.job_service import refresh_batch_counters
from app.services.meter_value import normalize_meter_reading, parse_meter_value
from app.services.reviewed_image_service import archive_reviewed_image, remove_reviewed_image


def _normalized_ai_bbox(
    image: ImageRecord, ai_result: AiResult, region_name: str
) -> ReadingBoundingBox | None:
    region = (ai_result.raw_result_json.get("regions") or {}).get(region_name)
    if not isinstance(region, list | tuple) or len(region) != 4:
        return None
    scale = min(1.0, 1600 / max(image.width, image.height))
    prepared_width = round(image.width * scale)
    prepared_height = round(image.height * scale)
    try:
        x, y, width, height = (float(value) for value in region)
        return ReadingBoundingBox(
            x=x / prepared_width,
            y=y / prepared_height,
            width=width / prepared_width,
            height=height / prepared_height,
        )
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _normalized_ai_reading_bbox(
    image: ImageRecord, ai_result: AiResult
) -> ReadingBoundingBox | None:
    return _normalized_ai_bbox(image, ai_result, "reading")


def _normalized_ai_meter_bbox(image: ImageRecord, ai_result: AiResult) -> ReadingBoundingBox | None:
    return _normalized_ai_bbox(image, ai_result, "meter")


def _stored_reading_polygon(reading: MeterReading | None) -> ReadingPolygon | None:
    if reading and reading.reading_polygon_json:
        try:
            return ReadingPolygon.model_validate(reading.reading_polygon_json)
        except (TypeError, ValueError):
            return None
    if (
        reading
        and reading.reading_bbox_x is not None
        and reading.reading_bbox_y is not None
        and reading.reading_bbox_width is not None
        and reading.reading_bbox_height is not None
    ):
        left, top = reading.reading_bbox_x, reading.reading_bbox_y
        right = left + reading.reading_bbox_width
        bottom = top + reading.reading_bbox_height
        return ReadingPolygon(
            points=[
                {"x": left, "y": top},
                {"x": right, "y": top},
                {"x": right, "y": bottom},
                {"x": left, "y": bottom},
            ]
        )
    return None


def _stored_meter_polygon(reading: MeterReading | None) -> ReadingPolygon | None:
    if reading and reading.meter_polygon_json:
        try:
            return ReadingPolygon.model_validate(reading.meter_polygon_json)
        except (TypeError, ValueError):
            return None
    return None


def _apply_result_filters(
    statement, image_status: str | None, search: str | None, review_status: str | None = None
):
    if review_status:
        statement = statement.where(
            func.coalesce(MeterReading.review_status, "PENDING") == review_status
        )
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


def get_result_status_counts(db: Session, search: str | None = None) -> ResultStatusCounts:
    """Return counts using the same status invariants as the operations queues."""
    effective_review_status = func.coalesce(MeterReading.review_status, "PENDING")
    statement = (
        select(
            func.count(ImageRecord.id)
            .filter(ImageRecord.status == ImageStatus.REVIEW_REQUIRED)
            .label("review_required"),
            func.count(ImageRecord.id)
            .filter(
                ImageRecord.status == ImageStatus.REVIEW_REQUIRED,
                effective_review_status == "PENDING",
            )
            .label("pending"),
            func.count(ImageRecord.id)
            .filter(
                ImageRecord.status == ImageStatus.REVIEW_REQUIRED,
                effective_review_status == "LABELED",
            )
            .label("labeled"),
            func.count(ImageRecord.id)
            .filter(
                ImageRecord.status == ImageStatus.CONFIRMED,
                effective_review_status == "CONFIRMED",
            )
            .label("confirmed"),
            func.count(ImageRecord.id)
            .filter(
                ImageRecord.status == ImageStatus.REJECTED,
                effective_review_status == "REJECTED",
            )
            .label("rejected"),
        )
        .select_from(ImageRecord)
        .join(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .outerjoin(Customer, Customer.id == MeterReading.matched_customer_id)
    )
    statement = _apply_result_filters(statement, None, search)
    row = db.execute(statement).one()
    return ResultStatusCounts(
        review_required=int(row.review_required or 0),
        pending=int(row.pending or 0),
        labeled=int(row.labeled or 0),
        confirmed=int(row.confirmed or 0),
        rejected=int(row.rejected or 0),
    )


def list_results(
    db: Session,
    offset: int,
    limit: int,
    image_status: str | None,
    search: str | None,
    review_status: str | None = None,
) -> tuple[list[ResultRow], int]:
    statement = (
        select(
            ImageRecord,
            AiResult,
            MeterReading,
            Customer,
            ConfirmedMonthlyReading.reading_month,
            func.count(ImageRecord.id).over().label("total_count"),
        )
        .join(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .outerjoin(Customer, Customer.id == MeterReading.matched_customer_id)
        .outerjoin(
            ConfirmedMonthlyReading, ConfirmedMonthlyReading.source_image_id == ImageRecord.id
        )
        .order_by(AiResult.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    statement = _apply_result_filters(statement, image_status, search, review_status)
    rows = db.execute(statement).all()
    items = [
        ResultRow(
            reading_month=month,
            image_id=image.id,
            original_filename=image.original_filename,
            image_width=image.width,
            image_height=image.height,
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
            reading_bbox=(
                ReadingBoundingBox(
                    x=reading.reading_bbox_x,
                    y=reading.reading_bbox_y,
                    width=reading.reading_bbox_width,
                    height=reading.reading_bbox_height,
                )
                if reading
                and reading.reading_bbox_x is not None
                and reading.reading_bbox_y is not None
                and reading.reading_bbox_width is not None
                and reading.reading_bbox_height is not None
                else None
            ),
            reading_polygon=_stored_reading_polygon(reading),
            ai_reading_bbox=_normalized_ai_reading_bbox(image, ai_result),
            meter_polygon=_stored_meter_polygon(reading),
            ai_meter_bbox=_normalized_ai_meter_bbox(image, ai_result),
        )
        for image, ai_result, reading, customer, month, _ in rows
    ]
    total = int(rows[0].total_count) if rows else 0
    if not rows and offset:
        count_statement = (
            select(func.count(ImageRecord.id))
            .join(AiResult, AiResult.image_id == ImageRecord.id)
            .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
            .outerjoin(Customer, Customer.id == MeterReading.matched_customer_id)
        )
        count_statement = _apply_result_filters(
            count_statement, image_status, search, review_status
        )
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
        .with_for_update(of=ImageRecord)
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
    if payload.action == "CONFIRM" and matched_customer is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Mã khách hàng phải tồn tại trong cơ sở dữ liệu trước khi xác nhận.",
        )
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
    old_bbox = (
        {
            "x": reading.reading_bbox_x,
            "y": reading.reading_bbox_y,
            "width": reading.reading_bbox_width,
            "height": reading.reading_bbox_height,
        }
        if reading.reading_bbox_x is not None
        and reading.reading_bbox_y is not None
        and reading.reading_bbox_width is not None
        and reading.reading_bbox_height is not None
        else None
    )
    old_polygon = reading.reading_polygon_json
    old_meter_polygon = reading.meter_polygon_json
    meter_was_submitted = "meter_polygon" in payload.model_fields_set
    new_meter_polygon = payload.meter_polygon.model_dump() if payload.meter_polygon else None
    bbox_was_submitted = "reading_bbox" in payload.model_fields_set
    polygon_was_submitted = "reading_polygon" in payload.model_fields_set
    new_polygon = payload.reading_polygon.model_dump() if payload.reading_polygon else None
    submitted_bbox = (
        payload.reading_polygon.bounding_box() if payload.reading_polygon else payload.reading_bbox
    )
    new_bbox = submitted_bbox.model_dump() if submitted_bbox else None
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

    if payload.action == "CONFIRM" and bbox_was_submitted and old_bbox != new_bbox:
        correction_count += 1
        changed_fields.append("reading_bbox")
        db.add(
            ManualCorrection(
                image_id=image_id,
                ai_result_id=ai_result.id,
                field_name="reading_bbox",
                old_value=json.dumps(old_bbox, ensure_ascii=False, sort_keys=True),
                new_value=json.dumps(new_bbox, ensure_ascii=False, sort_keys=True),
                reason=payload.reason,
                created_by=user.id,
            )
        )

    if payload.action == "CONFIRM" and polygon_was_submitted and old_polygon != new_polygon:
        correction_count += 1
        changed_fields.append("reading_polygon")
        db.add(
            ManualCorrection(
                image_id=image_id,
                ai_result_id=ai_result.id,
                field_name="reading_polygon",
                old_value=json.dumps(old_polygon, ensure_ascii=False, sort_keys=True),
                new_value=json.dumps(new_polygon, ensure_ascii=False, sort_keys=True),
                reason=payload.reason,
                created_by=user.id,
            )
        )

    if payload.action == "CONFIRM" and meter_was_submitted:
        if old_meter_polygon != new_meter_polygon:
            correction_count += 1
            changed_fields.append("meter_polygon")
            db.add(
                ManualCorrection(
                    image_id=image_id,
                    ai_result_id=ai_result.id,
                    field_name="meter_polygon",
                    old_value=json.dumps(old_meter_polygon, ensure_ascii=False, sort_keys=True),
                    new_value=json.dumps(new_meter_polygon, ensure_ascii=False, sort_keys=True),
                    reason=payload.reason,
                    created_by=user.id,
                )
            )
        meter_bbox = payload.meter_polygon.bounding_box() if payload.meter_polygon else None
        reading.meter_polygon_json = new_meter_polygon
        reading.meter_bbox_x = meter_bbox.x if meter_bbox else None
        reading.meter_bbox_y = meter_bbox.y if meter_bbox else None
        reading.meter_bbox_width = meter_bbox.width if meter_bbox else None
        reading.meter_bbox_height = meter_bbox.height if meter_bbox else None
        reading.meter_bbox_reviewed_by = user.id if meter_bbox else None
        reading.meter_bbox_reviewed_at = datetime.now(UTC) if meter_bbox else None

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
    if payload.action == "CONFIRM" and (bbox_was_submitted or polygon_was_submitted):
        if submitted_bbox:
            reading.reading_bbox_x = submitted_bbox.x
            reading.reading_bbox_y = submitted_bbox.y
            reading.reading_bbox_width = submitted_bbox.width
            reading.reading_bbox_height = submitted_bbox.height
            reading.reading_polygon_json = new_polygon if polygon_was_submitted else old_polygon
            reading.bbox_reviewed_by = user.id
            reading.bbox_reviewed_at = reading.reviewed_at
        else:
            reading.reading_bbox_x = None
            reading.reading_bbox_y = None
            reading.reading_bbox_width = None
            reading.reading_bbox_height = None
            reading.reading_polygon_json = None
            reading.bbox_reviewed_by = None
            reading.bbox_reviewed_at = None
    image.status = ImageStatus.CONFIRMED if payload.action == "CONFIRM" else ImageStatus.REJECTED
    reviewed_image_path = None
    removed_reviewed_image_path = None
    confirmed_record = None
    replaced_official_values: dict = {}
    removed_confirmed_record_id = None
    if payload.action == "CONFIRM":
        confirmed_record, replaced_official_values = save_confirmed_monthly_reading(
            db, image, reading, matched_customer, user.id, payload.reading_month
        )
        reviewed_image_path = archive_reviewed_image(
            image, matched_customer.customer_code, reading.reviewed_at
        )
    else:
        removed_confirmed_record_id = remove_confirmed_monthly_reading(db, image.id)
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
                "reading_bbox_before": old_bbox,
                "reading_bbox_after": (
                    {
                        "x": reading.reading_bbox_x,
                        "y": reading.reading_bbox_y,
                        "width": reading.reading_bbox_width,
                        "height": reading.reading_bbox_height,
                    }
                    if reading.reading_bbox_x is not None
                    else None
                ),
                "reading_polygon_before": old_polygon,
                "reading_polygon_after": reading.reading_polygon_json,
                "meter_polygon_before": old_meter_polygon,
                "meter_polygon_after": reading.meter_polygon_json,
                "customer_match_status": reading.customer_match_status,
                "matched_customer_id": (
                    str(reading.matched_customer_id) if reading.matched_customer_id else None
                ),
                "reviewed_image_path": reviewed_image_path,
                "removed_reviewed_image_path": removed_reviewed_image_path,
                "confirmed_monthly_record_id": (
                    str(confirmed_record.id) if confirmed_record else None
                ),
                "reading_month": (
                    confirmed_record.reading_month.isoformat() if confirmed_record else None
                ),
                "official_record_previous_values": replaced_official_values,
                "removed_confirmed_record_id": (
                    str(removed_confirmed_record_id) if removed_confirmed_record_id else None
                ),
            },
            ip_address=ip_address,
        )
    )
    db.commit()
    return reading
