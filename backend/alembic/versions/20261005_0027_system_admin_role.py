"""Separate system administration from daily operations.

Existing administrators retain their existing system privileges.
New accounts default to read-only access.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261005_0027"
down_revision = "20261003_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.execute("UPDATE users SET role = 'SUPER_ADMIN' WHERE role = 'ADMIN'")
    op.create_check_constraint(
        "ck_users_role", "users", "role IN ('SUPER_ADMIN', 'ADMIN', 'VIEWER')"
    )
    op.alter_column("users", "role", existing_type=sa.String(16), server_default="VIEWER")


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'SUPER_ADMIN'")
    op.create_check_constraint("ck_users_role", "users", "role IN ('ADMIN', 'VIEWER')")
    op.alter_column("users", "role", existing_type=sa.String(16), server_default="ADMIN")
