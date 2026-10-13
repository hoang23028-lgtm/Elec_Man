"""Generate private local configuration inside Docker, without a host Python install."""

import argparse
import os
import re
import secrets
from pathlib import Path


def create_environment(workspace: Path, filename: str, port: int) -> bool:
    if (
        not re.fullmatch(r"\.env(?:\.[a-zA-Z0-9_-]+)?", filename)
        or filename == ".env.example"
    ):
        raise ValueError("Use .env or a private .env.<name> file, not .env.example")
    if not 1 <= port <= 65535:
        raise ValueError("HTTP port must be between 1 and 65535")
    target = workspace / filename
    if target.is_symlink():
        raise ValueError("Configuration must not be a symbolic link")
    if target.exists():
        if not target.is_file() or target.stat().st_size == 0:
            raise ValueError("Existing configuration is empty or not a regular file")
        return False  # Never rotate database/session secrets on a repeat start.
    password = secrets.token_hex(32)
    overrides = {
        "FRONTEND_ORIGIN": "http://localhost" + (f":{port}" if port != 80 else ""),
        "NGINX_HTTP_PORT": str(port),
        "POSTGRES_PASSWORD": password,
        "DATABASE_URL": (
            f"postgresql+psycopg://electric_meter_app:{password}"
            "@postgres:5432/electric_meter_ai"
        ),
        "SESSION_SECRET": secrets.token_hex(48),
        "ADMIN_INITIAL_PASSWORD": "",
    }
    lines = []
    for line in (workspace / ".env.example").read_text(encoding="utf-8").splitlines():
        key = line.partition("=")[0]
        lines.append(f"{key}={overrides[key]}" if key in overrides else line)
    # O_EXCL prevents two installers overwriting each other's new configuration.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("/workspace"))
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--port", type=int, default=80)
    args = parser.parse_args()
    created = create_environment(args.workspace, args.env_file, args.port)
    print(
        "Created private configuration." if created else "Kept existing configuration."
    )


if __name__ == "__main__":
    main()
