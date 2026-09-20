"""add training pipeline

Revision ID: 20260920_0013
Revises: 20260920_0012
Create Date: 2026-09-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260920_0013"
down_revision = "20260920_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False, server_default="QUEUED"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("training_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dataset_hash", sa.String(64)),
        sa.Column(
            "metrics_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text()),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("model_id", sa.Uuid(), sa.ForeignKey("models.id", ondelete="SET NULL")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_training_runs_status", "training_runs", ["status"])
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
                "key": "training_auto_start",
                "value_json": 1,
                "description": "Tự tạo phiên huấn luyện khi đủ mẫu đã kiểm duyệt.",
            },
            {
                "key": "training_min_samples",
                "value_json": 20,
                "description": "Số ảnh đã kiểm duyệt tối thiểu để huấn luyện.",
            },
            {
                "key": "training_min_new_samples",
                "value_json": 10,
                "description": "Số mẫu mới tối thiểu từ lần huấn luyện thành công trước.",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_settings WHERE key LIKE 'training_%'")
    op.drop_table("training_runs")
