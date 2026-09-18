"""add operational query indexes

Revision ID: 20260918_0007
Revises: 20260918_0006
Create Date: 2026-09-18
"""

from alembic import op

revision = "20260918_0007"
down_revision = "20260918_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_processing_jobs_claim", "processing_jobs", ["status", "next_retry_at"])
    op.create_index("ix_processing_jobs_recovery", "processing_jobs", ["status", "started_at"])
    op.create_index("ix_images_batch_status", "images", ["batch_id", "status"])
    op.create_index("ix_ai_results_model_status", "ai_results", ["model_version", "status"])
    op.create_index("ix_ai_results_created_at", "ai_results", ["created_at"])
    op.create_index(
        "ix_meter_readings_review_ai", "meter_readings", ["review_status", "ai_result_id"]
    )
    op.create_index("ix_audit_logs_action_created", "audit_logs", ["action", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action_created", table_name="audit_logs")
    op.drop_index("ix_meter_readings_review_ai", table_name="meter_readings")
    op.drop_index("ix_ai_results_created_at", table_name="ai_results")
    op.drop_index("ix_ai_results_model_status", table_name="ai_results")
    op.drop_index("ix_images_batch_status", table_name="images")
    op.drop_index("ix_processing_jobs_recovery", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_claim", table_name="processing_jobs")
