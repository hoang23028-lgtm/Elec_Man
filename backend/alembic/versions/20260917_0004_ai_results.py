"""add immutable ai results

Revision ID: 20260917_0004
Revises: 20260917_0003
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260917_0004"
down_revision = "20260917_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("ai_results", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("image_id", sa.Uuid(), sa.ForeignKey("images.id", ondelete="RESTRICT"), nullable=False), sa.Column("model_version", sa.String(128), nullable=False), sa.Column("customer_id_ai", sa.String(128)), sa.Column("meter_reading_ai", sa.String(64)), sa.Column("customer_confidence", sa.Float(), nullable=False), sa.Column("meter_confidence", sa.Float(), nullable=False), sa.Column("detection_confidence", sa.Float(), nullable=False), sa.Column("image_quality_score", sa.Float(), nullable=False), sa.Column("final_confidence", sa.Float(), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("processing_time_ms", sa.Integer(), nullable=False), sa.Column("raw_result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("image_id"))
    op.create_index("ix_ai_results_image_id", "ai_results", ["image_id"])


def downgrade() -> None:
    op.drop_table("ai_results")
