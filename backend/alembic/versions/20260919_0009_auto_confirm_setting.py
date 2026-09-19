"""Describe the active automatic confirmation threshold.

Revision ID: 20260919_0009
Revises: 20260919_0008
Create Date: 2026-09-19
"""

import sqlalchemy as sa

from alembic import op

revision = "20260919_0009"
down_revision = "20260919_0008"
branch_labels = None
depends_on = None


def _update(description: str) -> None:
    table = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("description", sa.Text),
    )
    op.execute(
        table.update()
        .where(table.c.key == "confidence_ok_threshold")
        .values(description=description)
    )


def upgrade() -> None:
    _update(
        "Ngưỡng tự động xác nhận kết quả đầy đủ; chỉ kết quả có độ tin cậy lớn hơn "
        "ngưỡng này mới bỏ qua kiểm duyệt thủ công."
    )


def downgrade() -> None:
    _update("Độ tin cậy tối thiểu để mô hình sản xuất đề xuất tự động chấp nhận.")
