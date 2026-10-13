import importlib.util
import tarfile
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "backup_rehearsal", Path(__file__).resolve().parents[2] / "scripts/rehearse_backup.py"
)
rehearsal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearsal)


@pytest.fixture
def backup(tmp_path):
    lines = []
    for name in sorted(rehearsal.PAYLOADS):
        payload = f"Fixture for {name}".encode()
        (tmp_path / name).write_bytes(payload)
        lines.append(f"{sha256(payload).hexdigest()}  {name}")
    (tmp_path / "checksums.sha256").write_text("\n".join(lines), encoding="utf-8")
    return tmp_path


def test_all_backup_checksums_are_required_and_match(backup):
    assert set(rehearsal.verify_payloads(backup)) == rehearsal.PAYLOADS
    (backup / "database.sql").write_bytes(b"Changed dump")
    with pytest.raises(ValueError):
        rehearsal.verify_payloads(backup)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "traversal", "unknown", "malformed"])
def test_invalid_manifest_is_rejected_before_restore(backup, kind):
    path = backup / "checksums.sha256"
    lines = path.read_text().splitlines()
    if kind == "missing":
        lines.pop()
    elif kind == "duplicate":
        lines.append(lines[0])
    elif kind in ("traversal", "unknown"):
        lines[0] = "0" * 64 + ("  ../database.sql" if kind == "traversal" else "  other.sql")
    else:
        lines[0] = "invalid checksum"
    path.write_text("\n".join(lines))
    with pytest.raises(ValueError):
        rehearsal.verify_payloads(backup)


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("C:/windows", tarfile.REGTYPE),
        ("a\\escape", tarfile.REGTYPE),
        ("link", tarfile.SYMTYPE),
        ("hardlink", tarfile.LNKTYPE),
        ("device", tarfile.CHRTYPE),
    ],
)
def test_unsafe_archive_members_cannot_be_extracted(name, kind):
    member = tarfile.TarInfo(name)
    member.type = kind
    with pytest.raises(ValueError):
        rehearsal.safe_members([member])


def test_restored_files_are_checked_byte_for_byte(tmp_path):
    archive_path = tmp_path / "archive.tar.gz"
    data = b"Isolated archive fixture"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("images/test.png")
        member.size = len(data)
        archive.addfile(member, BytesIO(data))
    destination = tmp_path / "restore"
    destination.mkdir()
    result = rehearsal.restore_archive(archive_path, destination)
    assert result == {
        "restored_files": 1,
        "restored_bytes": len(data),
        "all_file_hashes_match": True,
    }
    assert (destination / "images/test.png").read_bytes() == data
