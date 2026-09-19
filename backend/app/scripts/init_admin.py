"""Create the one administrator account from environment-supplied credentials."""

import argparse
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User
from app.security.passwords import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Tạo tài khoản quản trị viên đầu tiên.")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = get_settings().admin_initial_password
    if password is None or len(password) < 12:
        print("ADMIN_INITIAL_PASSWORD phải có ít nhất 12 ký tự.", file=sys.stderr)
        return 2
    if not args.username.isidentifier() or not 3 <= len(args.username) <= 64:
        print("Tên đăng nhập phải gồm 3-64 chữ cái, chữ số hoặc dấu gạch dưới.", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Quản trị viên đã tồn tại; không tạo thêm tài khoản.", file=sys.stderr)
            return 1
        db.add(User(username=args.username, password_hash=hash_password(password), is_active=True))
        db.commit()
    print("Đã khởi tạo quản trị viên. Hãy xóa ADMIN_INITIAL_PASSWORD khỏi môi trường.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
