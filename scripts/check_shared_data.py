"""Verify the approved public snapshot without connecting to a live database."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["SESSION_SECRET"] = "snapshot-verification-not-a-login-key-123456789"
    sys.path.insert(0, str(ROOT / "backend"))
    from app.scripts.share_data import verify_snapshot

    data = verify_snapshot(ROOT / "data/snapshot")
    print(
        "Shared data verified:",
        {name: len(rows) for name, rows in data["tables"].items()},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
