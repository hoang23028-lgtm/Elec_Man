"""Consistent Docker backup with an OS lock and verification; no .env required.

Run manually, from Task Scheduler/systemd, or with --watch. Temporarily pauses
only running application writers. Existing credentials stay in Docker memory.
Backups contain private account data: never publish backups or their SQL files.
"""

import argparse
import json
import os
import re
import subprocess
import tarfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from rehearse_backup import PAYLOADS, digest, safe_members, verify_payloads

ROOT = Path(__file__).resolve().parents[1]
ALPINE = "alpine:3.21@sha256:ce64758a109eb420d874a118f87920e625e12d3634e03b4a5573fd9f6e5d3507"


def docker(*args, input=None, timeout=300):
    result = subprocess.run(
        ["docker", *args],
        input=input,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Docker backup operation failed; inspect private service logs."
        )
    return result.stdout.strip()


@contextmanager
def exclusive_lock(path):
    # Persistent inode, never unlink: deleting a lock file can permit two owners.
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def inventory(project):
    ids = docker(
        "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"
    ).splitlines()
    if not ids:
        raise ValueError("No containers belong to the requested project.")
    records = json.loads(docker("inspect", *ids))
    by_service = {}
    for record in records:
        labels = record["Config"]["Labels"]
        # Compose-built images carry project/service labels into unrelated test
        # containers. Only real Compose instances have the container config hash.
        if (
            not labels.get("com.docker.compose.config-hash")
            or labels.get("com.docker.compose.oneoff", "").lower() == "true"
        ):
            continue
        service = record["Config"]["Labels"].get("com.docker.compose.service")
        if service in by_service:
            raise ValueError(
                "Scaled services require a coordinated backup; this helper supports one instance."
            )
        by_service[service] = record
    if "postgres" not in by_service or "backend" not in by_service:
        raise ValueError("Project must contain its own postgres and backend.")
    return by_service


def volume_for(record, destination, project):
    mount = next(
        (
            m
            for m in record["Mounts"]
            if m["Destination"] == destination and m["Type"] == "volume"
        ),
        None,
    )
    if not mount:
        raise ValueError("Expected application volume is missing.")
    owner = json.loads(docker("volume", "inspect", mount["Name"]))[0]["Labels"] or {}
    if owner.get("com.docker.compose.project") != project:
        raise ValueError("Volume belongs to another project.")
    return mount["Name"]


def publish_status(image, volume, status):
    code = "import json,sys;from pathlib import Path;p=Path('/storage/.maintenance');p.mkdir(exist_ok=True);t=p/'backup-status.tmp';t.write_text(sys.stdin.read());t.replace(p/'backup-status.json')"
    docker(
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--user",
        "10001:10001",
        "--mount",
        f"type=volume,source={volume},target=/storage",
        "--entrypoint",
        "python",
        image,
        "-c",
        code,
        input=json.dumps(status),
    )


def archive_volume(volume, destination):
    # Stream as volume owner: no writable host bind and no root DAC override.
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--user",
        "10001:10001",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--mount",
        f"type=volume,source={volume},target=/source,readonly",
        ALPINE,
        "tar",
        "-czf",
        "-",
        "-C",
        "/source",
        ".",
    ]
    with destination.open("xb") as output:
        if os.name != "nt":
            os.chmod(destination, 0o600)
        result = subprocess.run(
            command, stdout=output, stderr=subprocess.PIPE, check=False, timeout=300
        )
    if result.returncode:
        raise RuntimeError("Could not archive the verified application volume.")


def backup(project, root):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", project):
        raise ValueError("Invalid project name.")
    root = root.resolve()
    if not root.is_relative_to(ROOT) or root == ROOT or root.is_symlink():
        raise ValueError("Backup root must be a directory inside this workspace.")
    root.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(root / f".{project}.backup.lock"):
        records = inventory(project)
        volume_for(records["postgres"], "/var/lib/postgresql/data", project)
        backend = records["backend"]
        helper_image = backend["Config"]["Image"]
        docker(
            "image", "inspect", helper_image
        )  # Must already exist, never implicit pull.
        env = dict(value.split("=", 1) for value in backend["Config"]["Env"])
        storage = volume_for(
            backend, env.get("STORAGE_ROOT", "/data/electric-meter-ai"), project
        )
        models = volume_for(backend, env.get("MODELS_ROOT", "/models"), project)
        writers = [
            r["Id"]
            for service, r in records.items()
            if service in {"backend", "worker", "trainer"} and r["State"]["Running"]
        ]
        destination = root / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
        destination.mkdir()
        status = {
            "status": "RUNNING",
            "verified": False,
            "completed_at": None,
            "error_code": None,
        }
        publish_status(helper_image, storage, status)
        stopped = []
        dump = f"/tmp/elec-man-backup-{uuid4().hex}.sql"
        try:
            # Stop each individually: finally restarts exactly the IDs successfully stopped.
            for container in writers:
                docker("stop", "--time", "30", container, timeout=60)
                stopped.append(container)
            postgres = records["postgres"]["Id"]
            docker(
                "exec",
                postgres,
                "sh",
                "-c",
                f'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f {dump}',
            )
            docker("cp", f"{postgres}:{dump}", str(destination / "database.sql"))
            for volume, name in (
                (storage, "storage.tar.gz"),
                (models, "models.tar.gz"),
            ):
                archive_volume(volume, destination / name)
            hashes = {}
            for name in sorted(PAYLOADS):
                with (destination / name).open("rb") as stream:
                    hashes[name] = digest(stream)
            (destination / "checksums.sha256").write_text(
                "".join(f"{value}  {name}\n" for name, value in hashes.items()),
                encoding="utf-8",
            )
            verify_payloads(destination)
            for name in ("storage.tar.gz", "models.tar.gz"):
                with tarfile.open(destination / name, "r:gz") as archive:
                    safe_members(archive)
            status = {
                "status": "COMPLETED",
                "verified": True,
                "completed_at": datetime.now(UTC).isoformat(),
                "error_code": None,
            }
            (destination / "managed-manifest.json").write_text(
                json.dumps(
                    {
                        **status,
                        "project": project,
                        "format": "elec-man-managed-backup-v1",
                        "writer_pause": True,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            status = {
                "status": "FAILED",
                "verified": False,
                "completed_at": datetime.now(UTC).isoformat(),
                "error_code": "BACKUP_FAILED",
            }
            raise
        finally:
            try:
                docker("exec", records["postgres"]["Id"], "rm", "-f", dump)
                publish_status(helper_image, storage, status)
            finally:
                failures = []
                for container in stopped:
                    try:
                        docker("start", container)
                    except RuntimeError:
                        failures.append(container[:12])
                if failures:
                    raise RuntimeError(
                        "Could not restart application writers; manual action required."
                    )
        return destination


def prune_verified(project, root, keep):
    """Opt-in deletion: only this helper's owned, verified, flat backup folders."""
    root = root.resolve()
    if (
        not root.is_relative_to(ROOT)
        or root == ROOT
        or keep < 1
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", project)
    ):
        raise ValueError("Unsafe backup retention scope.")
    with exclusive_lock(root / f".{project}.backup.lock"):
        candidates = []
        for directory in root.iterdir():
            if (
                directory.is_symlink()
                or not directory.is_dir()
                or not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", directory.name)
            ):
                continue
            resolved = directory.resolve()
            if resolved.parent != root:
                continue
            manifest = resolved / "managed-manifest.json"
            try:
                metadata = json.loads(manifest.read_text(encoding="utf-8"))
                if (
                    metadata.get("format") != "elec-man-managed-backup-v1"
                    or metadata.get("project") != project
                    or metadata.get("verified") is not True
                ):
                    continue
                if {p.name for p in resolved.iterdir()} != PAYLOADS | {
                    "checksums.sha256",
                    "managed-manifest.json",
                }:
                    continue
                verify_payloads(resolved)
            except (OSError, ValueError):
                continue
            candidates.append(resolved)
        removed = []
        for directory in sorted(candidates, reverse=True)[keep:]:
            for name in PAYLOADS | {"checksums.sha256", "managed-manifest.json"}:
                path = directory / name
                if path.is_symlink() or path.resolve().parent != directory:
                    raise ValueError("Unsafe retention file.")
            for name in PAYLOADS | {"checksums.sha256", "managed-manifest.json"}:
                (directory / name).unlink()
            directory.rmdir()
            removed.append(directory.name)
        return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="elec_man")
    parser.add_argument("--root", type=Path, default=ROOT / "backups")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run periodically in a host supervisor, without a Docker socket mount",
    )
    parser.add_argument("--interval-hours", type=float, default=24)
    parser.add_argument(
        "--keep",
        type=int,
        default=0,
        help="Explicitly authorize deletion of older verified managed backups; 0 keeps all",
    )
    args = parser.parse_args()
    if not 1 <= args.interval_hours <= 168:
        parser.error("interval must be 1–168 hours")
    if args.keep < 0:
        parser.error("keep must be nonnegative")
    while True:
        try:
            result = backup(args.project, args.root)
            print(f"Verified backup: {result}", flush=True)
            if args.keep:
                removed = prune_verified(args.project, args.root, args.keep)
                if removed:
                    print(
                        f"Permanently removed {len(removed)} older verified backups under the explicit retention policy.",
                        flush=True,
                    )
        except Exception:
            print(
                "Backup failed. Check private host/service logs; no credentials are printed.",
                flush=True,
            )
            if not args.watch:
                raise SystemExit(1) from None
        if not args.watch:
            break
        time.sleep(args.interval_hours * 3600)


if __name__ == "__main__":
    main()
