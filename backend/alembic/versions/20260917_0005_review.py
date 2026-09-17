"""add final readings and manual corrections

Revision ID: 20260917_0005
Revises: 20260917_0004
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260917_0005"
down_revision = "20260917_0004"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("meter_readings", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("image_id", sa.Uuid(), sa.ForeignKey("images.id", ondelete="RESTRICT"), nullable=False), sa.Column("ai_result_id", sa.Uuid(), sa.ForeignKey("ai_results.id", ondelete="RESTRICT"), nullable=False), sa.Column("final_customer_id", sa.String(128)), sa.Column("final_meter_reading", sa.String(64)), sa.Column("review_status", sa.String(24), nullable=False, server_default="PENDING"), sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("image_id"))
    op.create_index("ix_meter_readings_image_id", "meter_readings", ["image_id"])
    op.create_table("manual_corrections", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("image_id", sa.Uuid(), sa.ForeignKey("images.id", ondelete="RESTRICT"), nullable=False), sa.Column("ai_result_id", sa.Uuid(), sa.ForeignKey("ai_results.id", ondelete="RESTRICT"), nullable=False), sa.Column("field_name", sa.String(64), nullable=False), sa.Column("old_value", sa.Text()), sa.Column("new_value", sa.Text()), sa.Column("reason", sa.Text()), sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_manual_corrections_image_id", "manual_corrections", ["image_id"])
    op.create_index("ix_manual_corrections_ai_result_id", "manual_corrections", ["ai_result_id"])

def downgrade() -> None:
    op.drop_table("manual_corrections")
    op.drop_table("meter_readings")
