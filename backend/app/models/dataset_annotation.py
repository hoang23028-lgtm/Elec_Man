from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class DatasetAnnotation(Base):
    __tablename__ = "dataset_annotations"
    __table_args__ = (
        CheckConstraint(
            "partition IN ('UNASSIGNED','TRAIN','VALIDATION','HOLDOUT')",
            name="ck_dataset_partition",
        ),
        Index("ix_dataset_group_partition", "group_key", "partition"),
    )
    image_id: Mapped[UUID] = mapped_column(
        ForeignKey("images.id", ondelete="RESTRICT"), primary_key=True
    )
    group_key: Mapped[str | None] = mapped_column(String(64))
    partition: Mapped[str] = mapped_column(String(16), nullable=False, server_default="UNASSIGNED")
    identity_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    label_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    label_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000))
    holdout_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __mapper_args__ = {"version_id_col": revision}
