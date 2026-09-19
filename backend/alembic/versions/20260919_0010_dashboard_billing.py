"""add normalized meter values and dashboard billing price

Revision ID: 20260919_0010
Revises: 20260919_0009
Create Date: 2026-09-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260919_0010"
down_revision = "20260919_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meter_readings", sa.Column("reading_value", sa.Numeric(14, 3)))
    op.execute(
        """
        UPDATE meter_readings
        SET reading_value = REPLACE(TRIM(final_meter_reading), ',', '.')::numeric
        WHERE final_meter_reading IS NOT NULL
          AND TRIM(final_meter_reading) ~ '^[0-9]{1,11}([.,][0-9]{1,3})?$'
        """
    )
    op.create_index(
        "ix_meter_readings_customer_period",
        "meter_readings",
        ["final_customer_id", "reviewed_at"],
    )
    settings = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("value_json", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        settings,
        [
            {
                "key": "electricity_unit_price_vnd",
                "value_json": 2500,
                "description": (
                    "Đơn giá bình quân dùng để tạm tính tiền điện trên bảng điều khiển; "
                    "không thay thế hóa đơn chính thức."
                ),
            }
        ],
    )


def downgrade() -> None:
    settings = sa.table("system_settings", sa.column("key", sa.String))
    op.execute(settings.delete().where(settings.c.key == "electricity_unit_price_vnd"))
    op.drop_index("ix_meter_readings_customer_period", table_name="meter_readings")
    op.drop_column("meter_readings", "reading_value")
