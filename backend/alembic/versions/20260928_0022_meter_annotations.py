"""Store verified four-point polygons for complete electricity meters.

Revision ID: 20260928_0022
Revises: 20260928_0021
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260928_0022"
down_revision = "20260928_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meter_readings", sa.Column("meter_bbox_x", sa.Float(), nullable=True))
    op.add_column("meter_readings", sa.Column("meter_bbox_y", sa.Float(), nullable=True))
    op.add_column("meter_readings", sa.Column("meter_bbox_width", sa.Float(), nullable=True))
    op.add_column("meter_readings", sa.Column("meter_bbox_height", sa.Float(), nullable=True))
    op.add_column(
        "meter_readings",
        sa.Column("meter_polygon_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "meter_readings",
        sa.Column("meter_bbox_reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "meter_readings",
        sa.Column("meter_bbox_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_meter_readings_meter_bbox_reviewed_by_users",
        "meter_readings",
        "users",
        ["meter_bbox_reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_meter_readings_meter_bbox_reviewed_by_users",
        "meter_readings",
        type_="foreignkey",
    )
    op.drop_column("meter_readings", "meter_bbox_reviewed_at")
    op.drop_column("meter_readings", "meter_bbox_reviewed_by")
    op.drop_column("meter_readings", "meter_polygon_json")
    op.drop_column("meter_readings", "meter_bbox_height")
    op.drop_column("meter_readings", "meter_bbox_width")
    op.drop_column("meter_readings", "meter_bbox_y")
    op.drop_column("meter_readings", "meter_bbox_x")
