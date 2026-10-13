"""Store verified meter groups and permanently reserved holdout assignments."""

import sqlalchemy as sa

from alembic import op

revision = "20261013_0029"
down_revision = "20261012_0028"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dataset_annotations",
        sa.Column(
            "image_id", sa.Uuid(), sa.ForeignKey("images.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column("group_key", sa.String(64)),
        sa.Column("partition", sa.String(16), nullable=False, server_default="UNASSIGNED"),
        sa.Column("identity_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("label_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("label_revision", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(1000)),
        sa.Column("holdout_locked_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "partition IN ('UNASSIGNED','TRAIN','VALIDATION','HOLDOUT')",
            name="ck_dataset_partition",
        ),
    )
    op.create_index("ix_dataset_group_partition", "dataset_annotations", ["group_key", "partition"])


def downgrade():
    op.drop_table("dataset_annotations")
