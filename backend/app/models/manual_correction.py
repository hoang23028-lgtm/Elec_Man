from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class ManualCorrection(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "manual_corrections"
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="RESTRICT"), index=True)
    ai_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_results.id", ondelete="RESTRICT"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
