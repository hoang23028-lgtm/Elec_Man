"""Add customer master data and reading reconciliation fields.

Revision ID: 20260924_0015
Revises: 20260920_0014
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260924_0015"
down_revision = "20260920_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("customer_code", sa.String(length=128), nullable=False),
        sa.Column("lookup_key", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("electricity_route", sa.String(length=255), nullable=False),
        sa.Column("meter_serial", sa.String(length=128), nullable=False),
        sa.Column("initial_reading", sa.Integer(), nullable=False),
        sa.Column("usage_purpose", sa.String(length=64), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_code"),
        sa.UniqueConstraint("meter_serial"),
    )
    op.create_index("ix_customers_lookup_key", "customers", ["lookup_key"], unique=True)
    op.create_index("ix_customers_route", "customers", ["electricity_route"])
    op.add_column(
        "meter_readings",
        sa.Column("matched_customer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "meter_readings",
        sa.Column(
            "customer_match_status",
            sa.String(length=24),
            server_default="NOT_CHECKED",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_meter_readings_matched_customer",
        "meter_readings",
        "customers",
        ["matched_customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_meter_readings_customer_match",
        "meter_readings",
        ["customer_match_status", "matched_customer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_meter_readings_customer_match", table_name="meter_readings")
    op.drop_constraint(
        "fk_meter_readings_matched_customer", "meter_readings", type_="foreignkey"
    )
    op.drop_column("meter_readings", "customer_match_status")
    op.drop_column("meter_readings", "matched_customer_id")
    op.drop_index("ix_customers_route", table_name="customers")
    op.drop_index("ix_customers_lookup_key", table_name="customers")
    op.drop_table("customers")
