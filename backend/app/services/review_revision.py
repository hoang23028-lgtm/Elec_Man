from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.meter_reading import MeterReading


def check_review_revision(
    db: Session, reading: MeterReading | None, expected_revision: int | None
) -> None:
    """Call after locking the source image, before modifying its reading."""
    if expected_revision is None:
        return  # Internal service callers do not submit browser drafts.
    if reading is not None:
        # Refresh after a competing image lock was released: the joined SELECT
        # may have seen the reading before that transaction committed.
        db.refresh(reading)
    actual_revision = reading.revision if reading is not None else 0
    if actual_revision != expected_revision:
        raise HTTPException(
            status_code=412,
            detail="Dữ liệu ảnh đã được thay đổi. Bản nháp của bạn chưa được lưu. "
            "Hãy tải bản mới nhất và đối chiếu trước khi lưu lại.",
        )
