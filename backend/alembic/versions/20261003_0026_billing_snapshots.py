"""Preserve customer billing inputs at confirmation time.

Existing records can only be backfilled from the currently available customer data.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261003_0026"
down_revision = "20261003_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "confirmed_monthly_readings", sa.Column("initial_reading_snapshot", sa.Numeric(14, 0))
    )
    op.add_column("confirmed_monthly_readings", sa.Column("usage_purpose_snapshot", sa.String(64)))
    op.execute("""
        UPDATE confirmed_monthly_readings SET
            initial_reading_snapshot = (SELECT initial_reading FROM customers
                WHERE customers.id = confirmed_monthly_readings.customer_id),
            usage_purpose_snapshot = (SELECT usage_purpose FROM customers
                WHERE customers.id = confirmed_monthly_readings.customer_id)
    """)


def downgrade() -> None:
    op.drop_column("confirmed_monthly_readings", "usage_purpose_snapshot")
    op.drop_column("confirmed_monthly_readings", "initial_reading_snapshot")
