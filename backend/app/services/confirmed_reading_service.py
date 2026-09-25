from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.models.customer import Customer
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.services.storage_service import resolve_storage_path

_VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def reading_month(confirmed_at: datetime) -> date:
    local = confirmed_at.astimezone(_VIETNAM_TIMEZONE)
    return date(local.year, local.month, 1)


def save_confirmed_monthly_reading(
    db: Session,
    image: ImageRecord,
    reading: MeterReading,
    customer: Customer,
    confirmed_by: UUID | None,
) -> tuple[ConfirmedMonthlyReading, dict]:
    """Upsert one official customer/month record after successful confirmation."""
    if reading.reviewed_at is None or reading.reading_value is None:
        raise ValueError("Kết quả chưa có đủ dữ liệu xác nhận.")
    month = reading_month(reading.reviewed_at)
    source_record = db.scalar(
        select(ConfirmedMonthlyReading).where(ConfirmedMonthlyReading.source_image_id == image.id)
    )
    monthly_record = db.scalar(
        select(ConfirmedMonthlyReading).where(
            ConfirmedMonthlyReading.customer_id == customer.id,
            ConfirmedMonthlyReading.reading_month == month,
        )
    )
    if (
        source_record is not None
        and monthly_record is not None
        and source_record is not monthly_record
    ):
        db.delete(source_record)
        db.flush()
        record = monthly_record
    else:
        record = monthly_record or source_record
    replaced = {
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
