from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ConfirmedMonthlyReading(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Official monthly data created only after a reading is confirmed."""

    __tablename__ = "confirmed_monthly_readings"
    __table_args__ = (
        UniqueConstraint("customer_id", "reading_month", name="uq_confirmed_customer_month"),
        Index("ix_confirmed_readings_month", "reading_month"),
    )

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_image_id: Mapped[UUID] = mapped_column(
        ForeignKey("images.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    customer_code: Mapped[str] = mapped_column(String(128), nullable=False)
    reading_month: Mapped[date] = mapped_column(Date, nullable=False)
    meter_reading: Mapped[Decimal] = mapped_column(Numeric(14, 0), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    image_mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    image_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
