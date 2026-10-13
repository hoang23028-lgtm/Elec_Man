import importlib.util
import json
import sys
from hashlib import sha256
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("managed_backup", SCRIPTS / "managed_backup.py")
managed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(managed)


def test_backup_lock_is_exclusive_and_reusable(tmp_path):
    path = tmp_path / ".backup.lock"
    with managed.exclusive_lock(path):
        with pytest.raises(OSError):
            with managed.exclusive_lock(path):
                raise AssertionError("second owner acquired lock")
    assert path.exists()
    with managed.exclusive_lock(path):
        pass


def test_command_failure_never_echoes_credentials(monkeypatch):
    class Result:
        returncode = 1
        stdout = "secret-dsn"
        stderr = "secret-password"

    monkeypatch.setattr(managed.subprocess, "run", lambda *a, **kw: Result())
    with pytest.raises(RuntimeError) as error:
        managed.docker("inspect", "fixture")
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("project", ["../other", "ALL;docker rm", "UPPERCASE", ""])
def test_invalid_project_is_rejected_before_docker(project, tmp_path, monkeypatch):
    monkeypatch.setattr(managed, "docker", lambda *a, **kw: pytest.fail("Docker must not run"))
    with pytest.raises(ValueError):
        managed.backup(project, tmp_path)


def test_retention_only_deletes_verified_owned_flat_backups(tmp_path, monkeypatch):
    monkeypatch.setattr(managed, "ROOT", tmp_path)
    root = tmp_path / "backups"
    root.mkdir()
    for index in range(4):
        directory = root / f"2026101{index}T000000Z-0000000{index}"
        directory.mkdir()
        lines = []
        for name in managed.PAYLOADS:
            content = f"Synthetic private backup {name}".encode()
            (directory / name).write_bytes(content)
            lines.append(f"{sha256(content).hexdigest()}  {name}")
        (directory / "checksums.sha256").write_text("\n".join(lines), encoding="utf-8")
        (directory / "managed-manifest.json").write_text(
            json.dumps(
                {"format": "elec-man-managed-backup-v1", "project": "fixture", "verified": True}
            ),
            encoding="utf-8",
        )
    unknown = root / "historical-do-not-touch"
    unknown.mkdir()
    (unknown / "other.sql").write_text("fixture", encoding="utf-8")
    removed = managed.prune_verified("fixture", root, 2)
    assert len(removed) == 2
    assert unknown.is_dir() and (unknown / "other.sql").exists()
    assert len([p for p in root.iterdir() if p.is_dir()]) == 3


def test_failed_backup_restarts_exact_writers_and_does_not_claim_verified(tmp_path, monkeypatch):
    monkeypatch.setattr(managed, "ROOT", tmp_path)
    records = {
        key: {
            "Id": key,
            "State": {"Running": True},
            "Config": {"Image": "fixture-image", "Env": []},
        }
        for key in ("backend", "worker", "trainer", "postgres")
    }
    monkeypatch.setattr(managed, "inventory", lambda *_: records)
    monkeypatch.setattr(managed, "volume_for", lambda _, path, project: "fixture-volume")
    statuses = []
    calls = []
    monkeypatch.setattr(managed, "publish_status", lambda *a: statuses.append(a[-1]))

    def command(*args, **kwargs):
        calls.append(args)
        if args[0] == "exec" and "pg_dump" in args[-1]:
            raise RuntimeError("simulated dump failure")
        return ""

    monkeypatch.setattr(managed, "docker", command)
    with pytest.raises(RuntimeError, match="simulated"):
        managed.backup("fixture", tmp_path / "backups")
    assert {call[1] for call in calls if call[0] == "start"} == {"backend", "worker", "trainer"}
    assert statuses[-1]["verified"] is False and statuses[-1]["status"] == "FAILED"
    assert not list((tmp_path / "backups").rglob("managed-manifest.json"))
