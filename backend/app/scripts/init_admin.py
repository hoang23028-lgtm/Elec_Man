"""Create the one administrator account from environment-supplied credentials."""

import argparse
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User
from app.security.passwords import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the initial system administrator.")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = get_settings().admin_initial_password
    if password is None or len(password) < 12:
        print("ADMIN_INITIAL_PASSWORD must be set to at least 12 characters.", file=sys.stderr)
        return 2
    if not args.username.isidentifier() or not 3 <= len(args.username) <= 64:
        print("Username must contain 3-64 letters, digits, or underscores.", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Administrator already exists; refusing to create another.", file=sys.stderr)
            return 1
        db.add(User(username=args.username, password_hash=hash_password(password), is_active=True))
        db.commit()
    print("Administrator initialized. Remove ADMIN_INITIAL_PASSWORD from the environment now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
