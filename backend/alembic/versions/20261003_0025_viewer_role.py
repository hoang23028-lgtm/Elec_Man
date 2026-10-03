"""Allow read-only viewer accounts.

Revision ID: 20261003_0025
Revises: 20261003_0024
"""

from alembic import op

revision = "20261003_0025"
down_revision = "20261003_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role", "users", "role IN ('ADMIN', 'VIEWER')"
    )


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'VIEWER'")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('ADMIN')")
