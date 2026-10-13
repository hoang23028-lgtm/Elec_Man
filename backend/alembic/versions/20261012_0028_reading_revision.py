"""Prevent stale edits of human-reviewed meter readings."""

import sqlalchemy as sa

from alembic import op

revision = "20261012_0028"
down_revision = "20261005_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meter_readings", sa.Column("revision", sa.Integer(), nullable=False, server_default="1")
    )


def downgrade() -> None:
    op.drop_column("meter_readings", "revision")
