"""Add explicit user roles, repair counters, and prune expired sessions.

Revision ID: 20261003_0024
Revises: 20261001_0023
"""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0024"
down_revision = "20261001_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=16), nullable=False, server_default="ADMIN"),
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('ADMIN')")
    op.execute("DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP")
    op.execute(
        """
        UPDATE batches AS b SET
          review_count = (SELECT count(*) FROM images i WHERE i.batch_id = b.id AND i.status = 'REVIEW_REQUIRED'),
          ok_count = (SELECT count(*) FROM images i WHERE i.batch_id = b.id AND i.status = 'CONFIRMED'),
          ng_count = (SELECT count(*) FROM images i WHERE i.batch_id = b.id AND i.status = 'REJECTED')
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
