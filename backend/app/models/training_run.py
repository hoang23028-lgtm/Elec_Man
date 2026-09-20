from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class TrainingRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "training_runs"

    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False, default="PENDING")
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="QUEUED")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    training_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dataset_hash: Mapped[str | None] = mapped_column(String(64))
    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    model_id: Mapped[UUID | None] = mapped_column(ForeignKey("models.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
