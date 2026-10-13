"""Run API integration tests against a disposable, loopback-only PostgreSQL container."""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4


def docker(*args: str) -> str:
    timeout = 20 if args[0] == "info" else 90
    return subprocess.check_output(
        ["docker", *args], text=True, timeout=timeout
    ).strip()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    name = f"elec-man-integration-{uuid4().hex}"
    password = uuid4().hex
    docker("info", "--format", "{{.ServerVersion}}")
    created = False
    try:
        docker(
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "elec-man.integration=true",
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_DB=elec_man_integration",
            "-e",
            "POSTGRES_USER=integration",
            "-e",
            f"POSTGRES_PASSWORD={password}",
            "postgres:16-alpine",
        )
        created = True
        for _ in range(40):
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "integration"],
                check=False,
                capture_output=True,
                timeout=10,
            )
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Isolated PostgreSQL did not become ready")
        port = docker("port", name, "5432/tcp").rsplit(":", 1)[1]
        with tempfile.TemporaryDirectory(prefix="elec-man-integration-") as storage:
            env = {
                **os.environ,
                "APP_ENV": "test",
                "DATABASE_URL": (
                    f"postgresql+psycopg://integration:{password}@127.0.0.1:{port}"
                    "/elec_man_integration"
                ),
                "SESSION_SECRET": uuid4().hex + uuid4().hex,
                "ALLOWED_HOSTS": "testserver,localhost,127.0.0.1",
                "ENFORCE_HTTPS": "false",
                "STORAGE_ROOT": storage,
                "MODELS_ROOT": str(Path(storage) / "models"),
                "PYTHONPATH": str(root / "backend"),
                "ELEC_MAN_INTEGRATION": "1",
            }
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=root / "backend",
                env=env,
                check=True,
            )
            return subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "integration_tests",
                    "-q",
                    *sys.argv[1:],
                ],
                check=False,
                cwd=root / "backend",
                env=env,
            ).returncode
    finally:
        if created:
            # Exact random container created above; never touch application containers/volumes.
            docker("rm", "-fv", name)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        # Do not echo command arguments, which may contain disposable credentials.
        print(
            "Integration run failed: check Docker Desktop and the output above.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
