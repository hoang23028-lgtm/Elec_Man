"""Serve an isolated copy of the built application for browser verification.

No production volumes, database, credentials or reader endpoints are reused.
OCR is injected at the completed-worker boundary; this tests UI/API, not OCR.
Ctrl+C removes only the exact random containers/network created by this run.
"""

import argparse
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw

from verification_probe import probe_application

ROOT = Path(__file__).resolve().parents[1]
TEST_PASSWORD = "Isolated-browser-test-92!"  # Only disposable fixture accounts.


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, timeout=90).strip()


def unused_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def seed(url, env, verify=True):
    os.environ.update(env)
    sys.path.insert(0, str(ROOT / "backend"))
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.security.passwords import hash_password
    from app.services.ai_result_service import store_immutable_ai_result
    from app.services.job_service import claim_next_job, mark_job_completed

    with SessionLocal() as db:
        for role in ("VIEWER", "ADMIN", "SUPER_ADMIN"):
            db.add(
                User(
                    username=role.lower(),
                    role=role,
                    password_hash=hash_password(TEST_PASSWORD),
                )
            )
        db.commit()
    with httpx.Client(base_url=url, timeout=20, verify=verify) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "super_admin",
                "password": TEST_PASSWORD,
            },
        )
        response.raise_for_status()
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        for index in range(15):
            response = client.post(
                "/api/v1/customers",
                json={
                    "customer_code": f"TEST.{index + 1:03d}",
                    "full_name": f"Khách kiểm thử {index + 1}",
                    "address": "Dữ liệu thử riêng",
                    "electricity_route": "TEST",
                    "meter_serial": f"TEST{index + 1:03d}",
                    "initial_reading": 100,
                    "usage_purpose": "SINH_HOAT",
                },
            )
            response.raise_for_status()
        batch = client.post(
            "/api/v1/batches", json={"original_folder_name": "Kiểm thử giao diện"}
        )
        batch.raise_for_status()
        batch_id = batch.json()["id"]
        image_ids = []
        for index in range(15):
            picture = Image.new("RGB", (900, 700), (195 + index, 210, 220))
            drawing = ImageDraw.Draw(picture)
            drawing.rectangle((100, 100, 800, 600), outline="black", width=6)
            drawing.rectangle((220, 260, 630, 360), fill="black")
            drawing.text((240, 285), f"001{20 + index} kWh", fill="white", font_size=50)
            stream = BytesIO()
            picture.save(stream, format="PNG")
            upload = client.post(
                f"/api/v1/batches/{batch_id}/images",
                files={
                    "file": (
                        f"cong-to-thu-{index + 1:02d}.png",
                        stream.getvalue(),
                        "image/png",
                    ),
                },
            )
            upload.raise_for_status()
            image_ids.append(upload.json()["id"])
        client.post(f"/api/v1/batches/{batch_id}/start").raise_for_status()
    with SessionLocal() as db:
        for _ in image_ids:
            job = claim_next_job(db, "isolated-ui-fixture")
            result = {
                "model_version": "ui-fixture-not-ocr",
                "customer_id_ai": None,
                "meter_reading_ai": "00120",
                "customer_confidence": 0,
                "meter_confidence": 0.8,
                "detection_confidence": 0.8,
                "image_quality_score": 0.8,
                "final_confidence": 0.8,
                "status": "REVIEW_REQUIRED",
                "processing_time_ms": 1,
                "regions": {
                    "meter": [100, 100, 700, 500],
                    "reading": [220, 260, 410, 100],
                },
            }
            store_immutable_ai_result(db, job.image_id, result)
            db.commit()
            mark_job_completed(db, job.id, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use production HTTPS configuration with a temporary trusted test certificate",
    )
    parser.add_argument(
        "--probe", action="store_true", help="Run bounded HTTP checks and exit"
    )
    parser.add_argument("--report", type=Path)
    options = parser.parse_args()
    if not 1 <= options.minutes <= 120:
        parser.error("minutes must be between 1 and 120")
    if options.report and options.report.exists():
        parser.error("Choose a new report path")
    token = uuid4().hex[:12]
    network = f"elec-verify-{token}"
    created = []
    network_created = False
    with tempfile.TemporaryDirectory(prefix="elec-ui-test-") as temporary:
        # These directories contain only fake fixtures. Permit the non-root
        # container UID to access them on Linux as well as Windows Docker Desktop.
        Path(temporary).chmod(0o755)
        storage = Path(temporary) / "storage"
        storage.mkdir()
        storage.chmod(0o777)
        password = uuid4().hex
        web_port = unused_port()
        url = f"{'https' if options.https else 'http'}://127.0.0.1:{web_port}"
        verify = True
        http_url = None
        nginx_path = ROOT / "docker/nginx.conf"
        try:
            docker("network", "create", network)
            network_created = True

            def run(label, image, *args, alias=None):
                name = f"{network}-{label}"
                docker(
                    "run",
                    "-d",
                    "--name",
                    name,
                    "--label",
                    "elec-man.verification=true",
                    "--network",
                    network,
                    "--network-alias",
                    alias or label,
                    *args,
                    image,
                )
                created.append(name)
                return name

            postgres = run(
                "postgres",
                "postgres:16-alpine",
                "-p",
                "127.0.0.1::5432",
                "-e",
                "POSTGRES_DB=elec_man_integration",
                "-e",
                "POSTGRES_USER=integration",
                "-e",
                f"POSTGRES_PASSWORD={password}",
            )
            for _ in range(40):
                if (
                    subprocess.run(
                        ["docker", "exec", postgres, "pg_isready", "-U", "integration"],
                        capture_output=True,
                        timeout=10,
                    ).returncode
                    == 0
                ):
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Test PostgreSQL not ready")
            db_port = docker("port", postgres, "5432/tcp").rsplit(":", 1)[1]
            env = {
                **os.environ,
                "APP_ENV": "production" if options.https else "test",
                "SESSION_SECRET": uuid4().hex + uuid4().hex,
                "DATABASE_URL": f"postgresql+psycopg://integration:{password}@127.0.0.1:{db_port}/elec_man_integration",
                "ENFORCE_HTTPS": "true" if options.https else "false",
                "FRONTEND_ORIGIN": url,
                "ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
                "STORAGE_ROOT": str(storage),
                "MODELS_ROOT": str(storage / "models"),
                "PYTHONPATH": str(ROOT / "backend"),
            }
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=ROOT / "backend",
                env=env,
                check=True,
            )
            container_env = {
                **env,
                "STORAGE_ROOT": "/data",
                "MODELS_ROOT": "/models",
                "DATABASE_URL": f"postgresql+psycopg://integration:{password}@postgres:5432/elec_man_integration",
            }
            args = [
                "--read-only",
                "--tmpfs",
                "/tmp:size=64m",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "-v",
                f"{storage}:/data",
            ]
            for key in (
                "APP_ENV",
                "DATABASE_URL",
                "SESSION_SECRET",
                "ENFORCE_HTTPS",
                "FRONTEND_ORIGIN",
                "ALLOWED_HOSTS",
                "STORAGE_ROOT",
                "MODELS_ROOT",
            ):
                args.extend(("-e", f"{key}={container_env[key]}"))
            run("backend", "elec_man-backend:latest", *args)
            run("frontend", "elec_man-frontend:latest")
            nginx_args = []
            if options.https:
                certificate_dir = Path(temporary) / "tls"
                certificate_dir.mkdir()
                docker(
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--user",
                    "0",
                    "-v",
                    f"{certificate_dir}:/tls",
                    "--entrypoint",
                    "openssl",
                    "elec_man-backend:latest",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-days",
                    "1",
                    "-keyout",
                    "/tls/privkey.pem",
                    "-out",
                    "/tls/fullchain.pem",
                    "-subj",
                    "/CN=localhost",
                    "-addext",
                    "subjectAltName=DNS:localhost,IP:127.0.0.1",
                )
                verify = ssl.create_default_context(
                    cafile=str(certificate_dir / "fullchain.pem")
                )
                nginx_path = Path(temporary) / "nginx.conf"
                nginx_path.write_text(
                    (ROOT / "docker/nginx.https.conf.example")
                    .read_text()
                    .replace("meter.example.com", "localhost 127.0.0.1"),
                    encoding="utf-8",
                )
                http_port = unused_port()
                http_url = f"http://127.0.0.1:{http_port}"
                nginx_args = [
                    "-p",
                    f"127.0.0.1:{http_port}:80",
                    "-v",
                    f"{certificate_dir}:/etc/nginx/tls:ro",
                ]
            run(
                "nginx",
                "nginx:stable-alpine",
                "-p",
                f"127.0.0.1:{web_port}:{443 if options.https else 80}",
                "-v",
                f"{nginx_path}:/etc/nginx/conf.d/default.conf:ro",
                *nginx_args,
            )
            for _ in range(40):
                try:
                    if (
                        httpx.get(
                            url + "/api/v1/health/ready", timeout=3, verify=verify
                        ).status_code
                        == 200
                    ):
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("Test API not ready")
            seed(url, env, verify)
            if options.probe:
                report = probe_application(url, TEST_PASSWORD, verify, http_url)
                if options.report:
                    options.report.parent.mkdir(parents=True, exist_ok=True)
                    with options.report.open("x", encoding="utf-8") as stream:
                        json.dump(report, stream, ensure_ascii=False, indent=2)
                print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
                return
            print(
                f"READY {url}\nRoles: viewer / admin / super_admin\n"
                "Password: Isolated-browser-test-92! (disposable fixtures only)",
                flush=True,
            )
            print(
                "No live database or production volume is mounted. Ctrl+C cleans this sandbox.",
                flush=True,
            )
            deadline = time.monotonic() + options.minutes * 60
            while time.monotonic() < deadline:
                time.sleep(1)
        finally:
            for name in reversed(created):
                subprocess.run(
                    ["docker", "rm", "-fv", name], capture_output=True, timeout=60
                )
            if network_created:
                subprocess.run(
                    ["docker", "network", "rm", network],
                    capture_output=True,
                    timeout=30,
                )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Sandbox removed; live application unchanged.")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print(
            "Sandbox failed. Check Docker and the diagnostics above; live data was not used."
        )
        raise SystemExit(1) from None
