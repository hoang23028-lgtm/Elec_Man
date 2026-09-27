"""Store explicit input for queued OCR jobs.

Revision ID: 20260927_0019
Revises: 20260927_0018
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260927_0019"
down_revision = "20260927_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs",
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("processing_jobs", "input_json")
