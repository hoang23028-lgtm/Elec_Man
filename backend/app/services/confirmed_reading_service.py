from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.models.customer import Customer
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.services.storage_service import resolve_storage_path


def save_confirmed_monthly_reading(
    db: Session,
    image: ImageRecord,
    reading: MeterReading,
    customer: Customer,
    confirmed_by: UUID | None,
    selected_month: date | None = None,
) -> tuple[ConfirmedMonthlyReading, dict]:
    """Upsert one official customer/month record after successful confirmation."""
    if reading.reviewed_at is None or reading.reading_value is None:
        raise ValueError("Kết quả chưa có đủ dữ liệu xác nhận.")
    source_record = db.scalar(
        select(ConfirmedMonthlyReading).where(ConfirmedMonthlyReading.source_image_id == image.id)
    )
    month = selected_month or (source_record.reading_month if source_record else None)
    if month is None or month.day != 1:
        raise HTTPException(
            status_code=422, detail="Vui lòng chọn kỳ tháng ghi điện trước khi xác nhận."
        )
    monthly_record = db.scalar(
        select(ConfirmedMonthlyReading).where(
            ConfirmedMonthlyReading.customer_id == customer.id,
            ConfirmedMonthlyReading.reading_month == month,
        )
    )
    if monthly_record is not None and monthly_record.source_image_id != image.id:
        raise HTTPException(
            status_code=409,
            detail="Khách hàng đã có chỉ số trong kỳ này. Hãy chỉnh sửa bản ghi đã xác nhận.",
        )
    record = monthly_record or source_record
    replaced = {
        "reading_month_before": record.reading_month.isoformat() if record else None,
        "source_image_id_before": str(record.source_image_id) if record else None,
        "meter_reading_before": str(record.meter_reading) if record else None,
    }
    if record is None:
        record = ConfirmedMonthlyReading()
        db.add(record)

    image_path = resolve_storage_path(image.relative_path)
    record.customer_id = customer.id
    record.source_image_id = image.id
    record.customer_code = customer.customer_code
    record.reading_month = month
    record.meter_reading = Decimal(reading.reading_value).quantize(Decimal("1"))
    record.original_filename = image.original_filename
    record.image_mime_type = image.mime_type
    record.image_sha256 = image.sha256
    record.image_data = image_path.read_bytes()
    record.confirmed_at = reading.reviewed_at
    record.confirmed_by = confirmed_by
    db.flush()
    return record, replaced


def remove_confirmed_monthly_reading(db: Session, image_id: UUID) -> UUID | None:
    record = db.scalar(
        select(ConfirmedMonthlyReading).where(ConfirmedMonthlyReading.source_image_id == image_id)
    )
    if record is None:
        return None
    record_id = record.id
    db.delete(record)
    return record_id
