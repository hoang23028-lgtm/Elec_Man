"""add processing jobs

Revision ID: 20260917_0003
Revises: 20260917_0002
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260917_0003"
down_revision = "20260917_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("processing_jobs", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("image_id", sa.Uuid(), sa.ForeignKey("images.id", ondelete="RESTRICT"), nullable=False), sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"), sa.Column("priority", sa.Integer(), nullable=False, server_default="0"), sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("max_attempts", sa.Integer(), nullable=False), sa.Column("error_code", sa.String(64)), sa.Column("error_message", sa.Text()), sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text())), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("next_retry_at", sa.DateTime(timezone=True)), sa.Column("worker_id", sa.String(128)), sa.UniqueConstraint("image_id"))
    op.create_index("ix_processing_jobs_image_id", "processing_jobs", ["image_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])
    op.create_index("ix_processing_jobs_next_retry_at", "processing_jobs", ["next_retry_at"])


def downgrade() -> None:
    op.drop_table("processing_jobs")
