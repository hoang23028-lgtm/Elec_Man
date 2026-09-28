"""Raise supervised training quality gates.

Revision ID: 20260928_0021
Revises: 20260927_0020
"""

from alembic import op

revision = "20260928_0021"
down_revision = "20260927_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE system_settings
        SET value_json = '200'::jsonb,
            description = 'Số ảnh có vùng bốn điểm và chỉ số đã xác nhận tối thiểu để huấn luyện.'
        WHERE key = 'training_min_samples' AND value_json = '20'::jsonb
        """
    )
    op.execute(
        """
        UPDATE system_settings
        SET value_json = '25'::jsonb
        WHERE key = 'training_min_new_samples' AND value_json = '10'::jsonb
        """
    )


def downgrade() -> None:
    op.execute(
        "UPDATE system_settings SET value_json = '20'::jsonb "
        "WHERE key = 'training_min_samples' AND value_json = '200'::jsonb"
    )
    op.execute(
        "UPDATE system_settings SET value_json = '10'::jsonb "
        "WHERE key = 'training_min_new_samples' AND value_json = '25'::jsonb"
    )
