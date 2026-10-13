"""Restore a trusted backup into disposable resources, never the live deployment.

Database dump is executable SQL: use only backups made by this application.
PostgreSQL has no network or published port; archives have no links or traversal.
"""

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from uuid import uuid4

PAYLOADS = {"database.sql", "storage.tar.gz", "models.tar.gz"}


def digest(stream):
    result = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        result.update(chunk)
    return result.hexdigest()


def verify_payloads(directory):
    expected = {}
    for line in (
        (directory / "checksums.sha256").read_text(encoding="utf-8-sig").splitlines()
    ):
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s{2}([^\s]+)", line)
        if not match or match[2] not in PAYLOADS or match[2] in expected:
            raise ValueError(
                "Checksum manifest is invalid, duplicated or contains an unexpected path"
            )
        expected[match[2]] = match[1].lower()
    if set(expected) != PAYLOADS:
        raise ValueError("Checksum manifest must contain all three payloads")
    for name in PAYLOADS:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing, empty or linked backup payload: {name}")
        with path.open("rb") as stream:
            if digest(stream) != expected[name]:
                raise ValueError(f"Checksum mismatch: {name}")
    return expected


def safe_members(archive):
    members, seen = [], set()
    total_bytes = 0
    for member in archive:
        path = PurePosixPath(member.name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in member.name
            or ":" in member.name
            or not (member.isdir() or member.isfile())
            or str(path) in seen
        ):
            raise ValueError("Backup archive contains an unsafe or duplicate member")
        seen.add(str(path))
        total_bytes += member.size
        if len(seen) > 1_000_000 or total_bytes > 100 * 1024**3:
            raise ValueError("Backup archive exceeds rehearsal safety limits")
        members.append(member)
    return members


def restore_archive(path, destination):
    with tarfile.open(path, "r:gz") as archive:
        members = safe_members(archive)
        archive.extractall(destination, members=members, filter="data")
        count, size = 0, 0
        for member in members:
            if not member.isfile():
                continue
            restored = (destination / member.name).resolve()
            if not restored.is_relative_to(destination.resolve()):
                raise ValueError("Restored file escaped rehearsal directory")
            with archive.extractfile(member) as original, restored.open("rb") as copy:
                if digest(original) != digest(copy):
                    raise ValueError("Restored archive contents do not match")
            count += 1
            size += member.size
        return {
            "restored_files": count,
            "restored_bytes": size,
            "all_file_hashes_match": True,
        }


def docker(*args, timeout=90):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        # Commands and SQL diagnostics can contain credentials or personal data.
        raise RuntimeError(f"Docker {args[0]} failed during isolated restore")
    return result.stdout.strip()


def restore_database(directory, user):
    name = f"elec-restore-rehearsal-{uuid4().hex}"
    created = False
    try:
        docker(
            "run",
            "-d",
            "--name",
            name,
            "--network",
            "none",
            "--label",
            "elec-man.rehearsal=true",
            "--mount",
            f"type=bind,source={directory},target=/backup,readonly",
            "-e",
            f"POSTGRES_USER={user}",
            "-e",
            f"POSTGRES_PASSWORD={uuid4().hex}",
            "-e",
            "POSTGRES_DB=restore_rehearsal",
            "postgres:16-alpine",
        )
        created = True
        for _ in range(45):
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", user],
                check=False,
                capture_output=True,
                timeout=10,
            )
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Isolated restore database did not become ready")
        docker(
            "exec",
            name,
            "psql",
            "-U",
            user,
            "-d",
            "restore_rehearsal",
            "--set",
            "ON_ERROR_STOP=1",
            "--single-transaction",
            "-f",
            "/backup/database.sql",
            timeout=180,
        )
        counts = docker(
            "exec",
            name,
            "psql",
            "-U",
            user,
            "-d",
            "restore_rehearsal",
            "-At",
            "-c",
            "SELECT json_build_object("
            "'customers', (SELECT count(*) FROM customers),"
            "'images', (SELECT count(*) FROM images),"
            "'labels', (SELECT count(*) FROM meter_readings WHERE review_status='LABELED'),"
            "'confirmed_monthly_readings', (SELECT count(*) FROM confirmed_monthly_readings),"
            "'migration', (SELECT version_num FROM alembic_version))",
        )
        return json.loads(counts)
    finally:
        if created:
            docker("rm", "-fv", name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup_directory", type=Path)
    parser.add_argument(
        "--database-user",
        required=True,
        help="Original PostgreSQL role, not a password",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", args.database_user):
        parser.error("Invalid original database role")
    if args.output.exists():
        parser.error("Choose a new report path")
    directory = args.backup_directory.resolve(strict=True)
    checksums = verify_payloads(directory)
    with tempfile.TemporaryDirectory(prefix="elec-restore-files-") as temporary:
        archives = {}
        for name in ("storage.tar.gz", "models.tar.gz"):
            destination = Path(temporary) / name.removesuffix(".tar.gz")
            destination.mkdir()
            archives[name] = restore_archive(directory / name, destination)
        counts = restore_database(directory, args.database_user)
    report = {
        "backup_directory": str(directory),
        "checksums": checksums,
        "restored_database": counts,
        "archives": archives,
        "live_database_modified": False,
        "production_volumes_mounted": False,
        "rehearsal_resources_removed": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        RuntimeError,
        OSError,
        tarfile.TarError,
        subprocess.TimeoutExpired,
    ) as error:
        print(
            f"Rehearsal failed ({type(error).__name__}); live deployment was not mounted."
        )
        raise SystemExit(1) from None
