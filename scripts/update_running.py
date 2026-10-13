"""Update an existing local Compose deployment without replacing lost secrets.

Reads the current container environment into memory, takes a verified consistent
backup, migrates, then recreates application services. No .env is generated.
Only the repository's local Compose deployment is supported (not TLS overrides).
"""

import argparse
import json
import os
import subprocess

from managed_backup import ROOT, backup, docker, inventory


def compose(project, env, overlay, *args):
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            project,
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-f",
            "-",
            *args,
        ],
        input=json.dumps(overlay),
        env=env,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=420,
    )
    if result.returncode:
        # Compose can print interpolated credentials during an error: don't echo.
        raise RuntimeError(
            "Update failed; inspect private service logs. Backup is preserved."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="elec_man")
    args = parser.parse_args()
    records = inventory(args.project)
    configs = {
        key: dict(value.split("=", 1) for value in row["Config"]["Env"])
        for key, row in records.items()
    }
    backend = configs["backend"]
    if backend.get("ENFORCE_HTTPS", "false").lower() == "true":
        raise ValueError(
            "TLS deployments must use their explicit production overrides and original configuration."
        )
    nginx = records.get("nginx")
    ports = (nginx or {}).get("HostConfig", {}).get("PortBindings", {}).get(
        "80/tcp"
    ) or []
    if len(ports) != 1 or ports[0]["HostIp"] not in {"127.0.0.1", "::1"}:
        raise ValueError(
            "Only a single loopback-bound local deployment can use this helper."
        )
    env = {
        **os.environ,
        **backend,
        **{k: v for k, v in configs["postgres"].items() if k.startswith("POSTGRES_")},
        "NGINX_BIND_ADDRESS": ports[0]["HostIp"],
        "NGINX_HTTP_PORT": ports[0]["HostPort"],
    }
    overlay = {
        "services": {
            key: {"environment": value}
            for key, value in configs.items()
            if key
            in {
                "backend",
                "worker",
                "trainer",
                "postgres",
                "reader-parseq",
                "reader-ppocr",
                "frontend",
            }
        }
    }
    compose(args.project, env, overlay, "config", "--quiet")
    result = backup(args.project, ROOT / "backups")
    print(f"Verified pre-update backup: {result}", flush=True)
    writer_ids = [
        records[key]["Id"]
        for key in ("backend", "worker", "trainer")
        if key in records and records[key]["State"]["Running"]
    ]
    try:
        for container in writer_ids:
            docker("stop", "--time", "30", container, timeout=60)
        compose(args.project, env, overlay, "run", "--rm", "--no-deps", "migrate")
        compose(
            args.project,
            env,
            overlay,
            "up",
            "-d",
            "--no-build",
            "--wait",
            "--wait-timeout",
            "300",
        )
    except Exception:
        for container in writer_ids:
            try:
                docker("start", container)
            except RuntimeError:
                pass
        raise
    print(
        "Existing deployment updated; original credentials retained in memory, no secret file generated."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "Update failed. Check private logs and the preserved backup; no secrets are printed."
        )
        raise SystemExit(1) from None
