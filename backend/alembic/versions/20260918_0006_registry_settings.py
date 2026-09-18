"""add model registry and system settings

Revision ID: 20260918_0006
Revises: 20260917_0005
Create Date: 2026-09-18
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260918_0006"
down_revision = "20260917_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "models",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("model_type", sa.String(64), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column(
            "metrics_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default="TESTING"),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("model_name", "version", name="uq_models_name_version"),
    )
    op.create_index("ix_models_model_type", "models", ["model_type"])
    op.create_index("ix_models_status", "models", ["status"])
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value_json", postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
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
                "key": "confidence_ok_threshold",
                "value_json": 0.9,
                "description": (
                    "Minimum confidence for a future production model to propose auto-pass."
                ),
            },
            {
                "key": "confidence_review_threshold",
                "value_json": 0.65,
                "description": "Confidence boundary used to prioritize manual review.",
            },
            {
                "key": "max_upload_size_mb",
                "value_json": 20,
                "description": (
                    "Operational upload-size policy. Environment configuration remains "
                    "the enforcement source until restart."
                ),
            },
            {
                "key": "max_retry_count",
                "value_json": 3,
                "description": "Desired processing retry limit for newly deployed workers.",
            },
            {
                "key": "data_retention_days",
                "value_json": 365,
                "description": "Retention planning value. No automatic deletion is enabled.",
            },
            {
                "key": "worker_poll_interval_seconds",
                "value_json": 2.0,
                "description": "Desired worker polling interval applied on deployment restart.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("models")
