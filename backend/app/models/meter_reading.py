from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MeterReading(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meter_readings"
    __table_args__ = (Index("ix_meter_readings_review_ai", "review_status", "ai_result_id"),)
    image_id: Mapped[UUID] = mapped_column(
        ForeignKey("images.id", ondelete="RESTRICT"), unique=True, index=True
    )
    ai_result_id: Mapped[UUID] = mapped_column(ForeignKey("ai_results.id", ondelete="RESTRICT"))
    final_customer_id: Mapped[str | None] = mapped_column(String(128))
    final_meter_reading: Mapped[str | None] = mapped_column(String(64))
    reading_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    review_status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING")
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
