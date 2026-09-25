"""Add the reviewed image archive path.

Revision ID: 20260925_0016
Revises: 20260924_0015
"""

import sqlalchemy as sa

from alembic import op

revision = "20260925_0016"
down_revision = "20260924_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("images", sa.Column("reviewed_path", sa.String(length=500), nullable=True))
    op.create_unique_constraint("uq_images_reviewed_path", "images", ["reviewed_path"])


def downgrade() -> None:
    op.drop_constraint("uq_images_reviewed_path", "images", type_="unique")
    op.drop_column("images", "reviewed_path")
