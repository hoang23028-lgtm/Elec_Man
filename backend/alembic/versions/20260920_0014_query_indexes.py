"""add indexes for audit, training and model runtime queries

Revision ID: 20260920_0014
Revises: 20260920_0013
Create Date: 2026-09-20
"""

from alembic import op

revision = "20260920_0014"
down_revision = "20260920_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_batches_created_at", "batches", ["created_at"])
    op.create_index(
        "ix_meter_readings_training",
        "meter_readings",
        ["review_status", "reviewed_by"],
    )
    op.create_index(
        "ix_models_runtime",
        "models",
        ["model_type", "status", "activated_at"],
    )
    op.create_index(
        "ix_training_runs_claim",
        "training_runs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_training_runs_claim", table_name="training_runs")
    op.drop_index("ix_models_runtime", table_name="models")
    op.drop_index("ix_meter_readings_training", table_name="meter_readings")
    op.drop_index("ix_batches_created_at", table_name="batches")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
