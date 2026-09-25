"""Store confirmed monthly readings and their image in PostgreSQL.

Revision ID: 20260925_0017
Revises: 20260925_0016
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260925_0017"
down_revision = "20260925_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "confirmed_monthly_readings",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_image_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_code", sa.String(length=128), nullable=False),
        sa.Column("reading_month", sa.Date(), nullable=False),
        sa.Column("meter_reading", sa.Numeric(precision=14, scale=0), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("image_mime_type", sa.String(length=64), nullable=False),
        sa.Column("image_sha256", sa.String(length=64), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("meter_reading >= 0", name="ck_confirmed_meter_reading_nonnegative"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_image_id"], ["images.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "reading_month", name="uq_confirmed_customer_month"),
        sa.UniqueConstraint("source_image_id"),
    )
    op.create_index(
        "ix_confirmed_monthly_readings_customer_id",
        "confirmed_monthly_readings",
        ["customer_id"],
    )
    op.create_index(
        "ix_confirmed_readings_month",
        "confirmed_monthly_readings",
        ["reading_month"],
    )


def downgrade() -> None:
    op.drop_index("ix_confirmed_readings_month", table_name="confirmed_monthly_readings")
    op.drop_index(
        "ix_confirmed_monthly_readings_customer_id",
        table_name="confirmed_monthly_readings",
    )
    op.drop_table("confirmed_monthly_readings")
