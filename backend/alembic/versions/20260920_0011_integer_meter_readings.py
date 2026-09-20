"""normalize confirmed meter readings to integer wheels

Revision ID: 20260920_0011
Revises: 20260919_0010
Create Date: 2026-09-20
"""

from alembic import op

revision = "20260920_0011"
down_revision = "20260919_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE meter_readings
        SET final_meter_reading = SPLIT_PART(
                REPLACE(TRIM(final_meter_reading), ',', '.'), '.', 1
            ),
            reading_value = TRUNC(reading_value)
        WHERE final_meter_reading IS NOT NULL
          AND reading_value IS NOT NULL
        """
    )


def downgrade() -> None:
    # Fractional wheels cannot be reconstructed after normalization. Original
    # AI output remains available in ai_results/raw_result_json for traceability.
    pass
