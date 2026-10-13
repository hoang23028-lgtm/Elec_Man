"""Create the one administrator account from environment-supplied credentials."""

import argparse
import re
import sys

from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User
from app.security.passwords import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Tạo tài khoản quản trị viên đầu tiên.")
    parser.add_argument("--username")
    parser.add_argument(
        "--check", action="store_true", help="Exit 0 if a system admin exists, 1 otherwise"
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.check:
            return 0 if has_system_admin(db) else 1
    if not args.username or not re.fullmatch(r"[A-Za-z0-9._-]{3,64}", args.username):
        print(
            "Tên đăng nhập phải gồm 3-64 chữ cái, chữ số, dấu chấm, gạch ngang/ dưới.",
            file=sys.stderr,
        )
        return 2
    password = get_settings().admin_initial_password
    if password is None or not 12 <= len(password) <= 256:
        print("ADMIN_INITIAL_PASSWORD phải có 12-256 ký tự.", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 2026101301})
        if has_system_admin(db):
            print("Quản trị toàn hệ thống đã tồn tại; giữ nguyên tài khoản và mật khẩu.")
            return 0
        if db.scalar(select(User.id).where(User.username == args.username)) is not None:
            print(
                "Tên đăng nhập đã tồn tại. Chọn tên khác, không tự nâng quyền tài khoản.",
                file=sys.stderr,
            )
            return 2
        db.add(
            User(
                username=args.username,
                password_hash=hash_password(password),
                is_active=True,
                role="SUPER_ADMIN",
            )
        )
        db.commit()
    print("Đã khởi tạo quản trị viên. Hãy xóa ADMIN_INITIAL_PASSWORD khỏi môi trường.")
    return 0


def has_system_admin(db) -> bool:
    # A locked account still counts: installation must not bypass an intentional lock.
    return (
        db.scalar(
            select(User.id).where(User.role == "SUPER_ADMIN", User.deleted_at.is_(None)).limit(1)
        )
        is not None
    )


if __name__ == "__main__":
    raise SystemExit(main())
