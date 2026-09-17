"""add batches and images

Revision ID: 20260917_0002
Revises: 20260917_0001
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260917_0002"
down_revision = "20260917_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("batches", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("batch_code", sa.String(40), nullable=False), sa.Column("original_folder_name", sa.String(255), nullable=False), sa.Column("total_images", sa.Integer(), nullable=False, server_default="0"), sa.Column("uploaded_images", sa.Integer(), nullable=False, server_default="0"), sa.Column("processed_images", sa.Integer(), nullable=False, server_default="0"), sa.Column("ok_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("ng_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("status", sa.String(24), nullable=False, server_default="UPLOADING"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("batch_code"))
    op.create_index("ix_batches_batch_code", "batches", ["batch_code"])
    op.create_table("images", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("stored_filename", sa.String(255), nullable=False), sa.Column("relative_path", sa.String(500), nullable=False), sa.Column("thumbnail_path", sa.String(500), nullable=False), sa.Column("file_size", sa.Integer(), nullable=False), sa.Column("mime_type", sa.String(64), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("width", sa.Integer(), nullable=False), sa.Column("height", sa.Integer(), nullable=False), sa.Column("status", sa.String(24), nullable=False, server_default="UPLOADED"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("stored_filename"), sa.UniqueConstraint("relative_path"), sa.UniqueConstraint("batch_id", "sha256", name="uq_images_batch_sha256"))
    op.create_index("ix_images_batch_id", "images", ["batch_id"])
    op.create_index("ix_images_sha256", "images", ["sha256"])


def downgrade() -> None:
    op.drop_table("images")
    op.drop_table("batches")
