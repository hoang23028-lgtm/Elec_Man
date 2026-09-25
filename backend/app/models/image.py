from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ImageStatus(StrEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    AI_COMPLETED = "AI_COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ImageRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "images"
    __table_args__ = (
        UniqueConstraint("batch_id", "sha256", name="uq_images_batch_sha256"),
        Index("ix_images_batch_status", "batch_id", "status"),
    )

    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("batches.id", ondelete="RESTRICT"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    relative_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    thumbnail_path: Mapped[str] = mapped_column(String(500), nullable=False)
    reviewed_path: Mapped[str | None] = mapped_column(String(500), unique=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=ImageStatus.UPLOADED)
