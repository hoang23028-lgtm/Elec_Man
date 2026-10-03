"""Align the processing queue index with worker claim order.

Revision ID: 20261001_0023
Revises: 20260928_0022
"""

import sqlalchemy as sa

from alembic import op

revision = "20261001_0023"
down_revision = "20260928_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Each column below already has a unique-constraint index. Maintaining a
    # second identical B-tree only slows inserts and updates.
    for index_name, table_name in (
        ("ix_ai_results_image_id", "ai_results"),
        ("ix_batches_batch_code", "batches"),
        ("ix_meter_readings_image_id", "meter_readings"),
        ("ix_processing_jobs_image_id", "processing_jobs"),
        ("ix_sessions_token_hash", "sessions"),
        ("ix_users_username", "users"),
    ):
        op.drop_index(index_name, table_name=table_name)
    op.drop_index("ix_processing_jobs_claim", table_name="processing_jobs")
    op.create_index(
        "ix_processing_jobs_claim",
        "processing_jobs",
        ["status", sa.text("priority DESC"), "created_at", "next_retry_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_claim", table_name="processing_jobs")
    op.create_index(
        "ix_processing_jobs_claim",
        "processing_jobs",
        ["status", "next_retry_at"],
    )
    for index_name, table_name, column_name in (
        ("ix_ai_results_image_id", "ai_results", "image_id"),
        ("ix_batches_batch_code", "batches", "batch_code"),
        ("ix_meter_readings_image_id", "meter_readings", "image_id"),
        ("ix_processing_jobs_image_id", "processing_jobs", "image_id"),
        ("ix_sessions_token_hash", "sessions", "session_token_hash"),
        ("ix_users_username", "users", "username"),
    ):
        op.create_index(index_name, table_name, [column_name])
