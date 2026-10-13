"""Create the explicitly approved public snapshot, never a raw credential-bearing dump."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def docker(*args, timeout=90, env=None):
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )
    if result.returncode:
        # Docker diagnostics/env inspection can contain credentials: do not print them.
        for line in result.stdout.splitlines():
            if re.fullmatch(
                r"Shared data operation failed \([A-Za-z]+\); check private diagnostics\.",
                line,
            ):
                print(line)
        raise RuntimeError(f"Docker {args[0]} failed during data export")
    return result.stdout.strip()


def container_for(project, service):
    names = docker(
        "ps",
        "-q",
        "--filter",
        f"label=com.docker.compose.project={project}",
        "--filter",
        f"label=com.docker.compose.service={service}",
    ).splitlines()
    if len(names) != 1:
        raise ValueError(f"Expected exactly one running {service} container")
    return names[0]


def export(project, destination):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", project):
        raise ValueError("Invalid Compose project name")
    if destination.exists() or not destination.resolve().is_relative_to(ROOT):
        raise ValueError("Choose a new export directory inside the repository")
    volumes = {}
    for kind in ("storage", "model"):
        name = f"{project}_{kind}_data"
        info = json.loads(docker("volume", "inspect", name))[0]
        if info["Labels"].get("com.docker.compose.project") != project:
            raise ValueError("Volume belongs to a different project")
        volumes[kind] = name
    network = f"{project}_data"
    network_info = json.loads(docker("network", "inspect", network))[0]
    if network_info["Labels"].get("com.docker.compose.project") != project:
        raise ValueError("Network belongs to a different project")
    writers = [
        container_for(project, service) for service in ("backend", "worker", "trainer")
    ]
    backend_info = json.loads(docker("inspect", writers[0]))[0]
    worker_image = json.loads(docker("inspect", writers[1]))[0]["Config"]["Image"]
    original_env = dict(
        item.split("=", 1) for item in backend_info["Config"]["Env"] if "=" in item
    )
    environment = os.environ.copy()
    environment["DATABASE_URL"] = original_env["DATABASE_URL"]
    name = f"elec-public-export-{uuid4().hex}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        print(
            "Temporarily stopping application writers to capture a consistent snapshot.",
            flush=True,
        )
        docker("stop", *writers)
        docker(
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            network,
            "--user",
            f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "0",
            "--read-only",
            "--tmpfs",
            "/tmp:size=128m,mode=1777",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "DAC_READ_SEARCH",
            "--security-opt",
            "no-new-privileges",
            "--mount",
            f"type=volume,source={volumes['storage']},target=/source/storage,readonly",
            "--mount",
            f"type=volume,source={volumes['model']},target=/source/models,readonly",
            "--mount",
            f"type=bind,source={ROOT / 'backend/app/scripts/share_data.py'},target=/app/app/scripts/share_data.py,readonly",
            "--mount",
            f"type=bind,source={destination.parent},target=/output",
            "--env",
            "DATABASE_URL",
            "--env",
            "APP_ENV=test",
            "--env",
            "SESSION_SECRET=public-export-not-an-authentication-key-123456789",
            "--env",
            "STORAGE_ROOT=/source/storage",
            "--env",
            "MODELS_ROOT=/source/models",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--entrypoint",
            "python",
            worker_image,
            "-m",
            "app.scripts.share_data",
            "export",
            f"/output/{destination.name}",
            "--with-training",
            timeout=300,
            env=environment,
        )
    finally:
        # Only the exact inspected running containers above; no Compose/env secret regeneration.
        try:
            docker("rm", "-f", name)
        except RuntimeError:
            pass  # --rm already removed it after a completed run.
        docker("start", *writers)
    # Reject any known deployment secret accidentally embedded in an output file.
    postgres = json.loads(docker("inspect", container_for(project, "postgres")))[0]
    postgres_env = dict(
        item.split("=", 1) for item in postgres["Config"]["Env"] if "=" in item
    )
    secrets = [
        original_env.get("SESSION_SECRET"),
        postgres_env.get("POSTGRES_PASSWORD"),
    ]
    for path in destination.rglob("*"):
        if path.is_file():
            payload = path.read_bytes()
            if any(
                secret and len(secret) >= 8 and secret.encode() in payload
                for secret in secrets
            ):
                raise ValueError(
                    "Known deployment credential found; snapshot must not be published"
                )
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {"counts": manifest["counts"], "training": manifest["training"]},
            ensure_ascii=False,
        )
    )
    print("Writers restarted. Original credentials were not written to the snapshot.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", default="elec_man")
    parser.add_argument("--output", type=Path, default=ROOT / "data/snapshot")
    parser.add_argument("--confirm-public-data", action="store_true", required=True)
    args = parser.parse_args()
    export(args.project_name, args.output.resolve())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            f"Public data export failed ({type(error).__name__}); nothing was uploaded."
        )
        raise SystemExit(2) from None
