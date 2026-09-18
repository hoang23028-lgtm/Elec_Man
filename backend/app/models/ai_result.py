from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class AiResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_results"
    __table_args__ = (
        Index("ix_ai_results_model_status", "model_version", "status"),
        Index("ix_ai_results_created_at", "created_at"),
    )

    image_id: Mapped[UUID] = mapped_column(
        ForeignKey("images.id", ondelete="RESTRICT"), unique=True, index=True
    )
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id_ai: Mapped[str | None] = mapped_column(String(128))
    meter_reading_ai: Mapped[str | None] = mapped_column(String(64))
    customer_confidence: Mapped[float] = mapped_column(nullable=False)
    meter_confidence: Mapped[float] = mapped_column(nullable=False)
    detection_confidence: Mapped[float] = mapped_column(nullable=False)
    image_quality_score: Mapped[float] = mapped_column(nullable=False)
    final_confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
