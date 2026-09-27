"""Store human-verified meter reading regions.

Revision ID: 20260927_0018
Revises: 20260925_0017
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260927_0018"
down_revision = "20260925_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meter_readings", sa.Column("reading_bbox_x", sa.Float(), nullable=True))
    op.add_column("meter_readings", sa.Column("reading_bbox_y", sa.Float(), nullable=True))
    op.add_column("meter_readings", sa.Column("reading_bbox_width", sa.Float(), nullable=True))
    op.add_column("meter_readings", sa.Column("reading_bbox_height", sa.Float(), nullable=True))
    op.add_column(
        "meter_readings",
        sa.Column("bbox_reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "meter_readings",
        sa.Column("bbox_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_meter_readings_bbox_reviewed_by_users",
        "meter_readings",
        "users",
        ["bbox_reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_meter_readings_bbox_complete",
        "meter_readings",
        "(reading_bbox_x IS NULL AND reading_bbox_y IS NULL AND "
        "reading_bbox_width IS NULL AND reading_bbox_height IS NULL) OR "
        "(reading_bbox_x IS NOT NULL AND reading_bbox_y IS NOT NULL AND "
        "reading_bbox_width IS NOT NULL AND reading_bbox_height IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_meter_readings_bbox_bounds",
        "meter_readings",
        "reading_bbox_x IS NULL OR (reading_bbox_x >= 0 AND reading_bbox_y >= 0 AND "
        "reading_bbox_width > 0 AND reading_bbox_height > 0 AND "
        "reading_bbox_x + reading_bbox_width <= 1 AND "
        "reading_bbox_y + reading_bbox_height <= 1)",
    )
    op.create_index(
        "ix_meter_readings_training_bbox",
        "meter_readings",
        ["review_status", "bbox_reviewed_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_meter_readings_training_bbox", table_name="meter_readings")
    op.drop_constraint("ck_meter_readings_bbox_bounds", "meter_readings", type_="check")
    op.drop_constraint("ck_meter_readings_bbox_complete", "meter_readings", type_="check")
    op.drop_constraint(
        "fk_meter_readings_bbox_reviewed_by_users", "meter_readings", type_="foreignkey"
    )
    op.drop_column("meter_readings", "bbox_reviewed_at")
    op.drop_column("meter_readings", "bbox_reviewed_by")
    op.drop_column("meter_readings", "reading_bbox_height")
    op.drop_column("meter_readings", "reading_bbox_width")
    op.drop_column("meter_readings", "reading_bbox_y")
    op.drop_column("meter_readings", "reading_bbox_x")
