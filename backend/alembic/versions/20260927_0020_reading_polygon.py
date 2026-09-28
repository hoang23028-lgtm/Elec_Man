"""Store four-point reading polygons.

Revision ID: 20260927_0020
Revises: 20260927_0019
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260927_0020"
down_revision = "20260927_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meter_readings",
        sa.Column(
            "reading_polygon_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("meter_readings", "reading_polygon_json")
