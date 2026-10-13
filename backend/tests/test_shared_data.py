import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.scripts import share_data
from app.security.passwords import verify_password


def test_sanitization_keeps_labels_but_removes_nested_credentials():
    source = {
        "customer_code": "PN2.001",
        "label": "00123",
        "nested": {"session_token": "sensitive", "password": "sensitive", "points": [1, 2]},
        "url": "postgresql+psycopg://actor:fixture@postgres/db",
        "hash": "$argon2id$v=19$m=123$fixture$fixture",
    }
    result = share_data.sanitize(source)
    assert result["customer_code"] == "PN2.001" and result["label"] == "00123"
    assert result["nested"] == {"points": [1, 2]}
    assert result["url"] == "[REDACTED]" and result["hash"] == "[REDACTED]"


def test_archived_actors_keep_foreign_keys_but_cannot_log_in():
    actor_id = uuid4()
    actor = share_data.archived_actor(
        {"id": actor_id, "created_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}
    )
    assert actor["id"] == str(actor_id) and actor["is_active"] is False
    assert actor["role"] == "VIEWER" and actor["password_hash"] == "!"
    assert not verify_password(actor["password_hash"], "any-password")


@pytest.mark.parametrize(
    "action", ["LOGIN_SUCCESS", "LOGOUT", "USER_UPDATE", "USER_PASSWORD_CHANGE", "REGISTER"]
)
def test_authentication_audit_is_not_shared(action):
    assert share_data.authentication_audit(action)
    assert not share_data.authentication_audit("SAVE_TRAINING_LABEL")


@pytest.mark.parametrize("path", ["../escape", "/absolute", "a/../b", "C:/file", "a\\file"])
def test_snapshot_paths_cannot_escape(tmp_path, path):
    with pytest.raises(ValueError):
        share_data.safe_path(tmp_path, path)


def test_normal_paths_and_binary_date_decimal_types_round_trip(tmp_path):
    assert share_data.safe_path(tmp_path, "original/image.jpg") == tmp_path / "original/image.jpg"
    row = {
        "customer_id": str(uuid4()),
        "reading_month": "2026-10-01",
        "confirmed_at": "2026-10-13T07:00:00+00:00",
        "meter_reading": "1234",
        "image_data": share_data.encode(b"image-bytes"),
    }
    decoded = share_data.decode_row(ConfirmedMonthlyReading.__table__, row)
    assert decoded["reading_month"].day == 1
    assert decoded["meter_reading"] == Decimal(1234)
    assert decoded["image_data"] == b"image-bytes"
    assert decoded["confirmed_at"].tzinfo is not None


def test_unknown_database_columns_are_rejected():
    with pytest.raises(ValueError):
        share_data.decode_row(ConfirmedMonthlyReading.__table__, {"unexpected_sql": "DROP TABLE"})


@pytest.fixture
def snapshot(tmp_path):
    tables = {table.name: [] for table in share_data.TABLES}
    tables["users"] = [
        share_data.archived_actor(
            {"id": uuid4(), "created_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}
        )
    ]
    data = {"format": share_data.FORMAT, "migration": "fixture", "tables": tables}
    share_data.write_json(tmp_path / "database.json", data)
    (tmp_path / "storage").mkdir()
    (tmp_path / "storage/image.jpg").write_bytes(b"synthetic-fixture")
    rewrite_manifest(tmp_path, data)
    return tmp_path


def rewrite_manifest(directory, data):
    files = {
        path.relative_to(directory).as_posix(): {
            "sha256": share_data.file_digest(path),
            "bytes": path.stat().st_size,
        }
        for path in directory.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "format": share_data.FORMAT,
        "authentication_exported": False,
        "migration": data["migration"],
        "counts": {key: len(value) for key, value in data["tables"].items()},
        "files": files,
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_snapshot_is_verified_without_running_sql(snapshot):
    assert share_data.verify_snapshot(snapshot)["tables"]["users"][0]["is_active"] is False


@pytest.mark.parametrize("kind", ["active", "hash", "session"])
def test_credential_payload_is_rejected_even_with_new_checksums(snapshot, kind):
    path = snapshot / "database.json"
    data = json.loads(path.read_text())
    if kind == "active":
        data["tables"]["users"][0]["is_active"] = True
    elif kind == "hash":
        data["tables"]["users"][0]["password_hash"] = "not-the-disabled-sentinel"
    else:
        data["tables"]["sessions"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    rewrite_manifest(snapshot, data)
    with pytest.raises(ValueError):
        share_data.verify_snapshot(snapshot)


def test_changed_or_unlisted_files_are_rejected(snapshot):
    (snapshot / "storage/image.jpg").write_bytes(b"changed")
    with pytest.raises(ValueError):
        share_data.verify_snapshot(snapshot)


def test_unlisted_private_file_is_rejected(snapshot):
    (snapshot / ".env").write_text("private-fixture")
    with pytest.raises(ValueError):
        share_data.verify_snapshot(snapshot)


def test_declared_private_file_is_still_rejected(snapshot):
    (snapshot / ".env").write_text("password=private-fixture")
    data = json.loads((snapshot / "database.json").read_text())
    rewrite_manifest(snapshot, data)
    with pytest.raises(ValueError):
        share_data.verify_snapshot(snapshot)


def test_existing_database_is_not_overwritten(snapshot, tmp_path):
    database = MagicMock()
    connection = database.begin.return_value.__enter__.return_value
    connection.dialect.name = "postgresql"
    connection.scalar.return_value = 1
    assert (
        share_data.import_snapshot(snapshot, tmp_path / "data", tmp_path / "models", database)
        is False
    )
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("damaged", ["missing", "corrupt"])
def test_existing_database_does_not_require_a_valid_snapshot(tmp_path, damaged):
    if damaged == "corrupt":
        (tmp_path / "manifest.json").write_text("not-json", encoding="utf-8")
    database = MagicMock()
    connection = database.begin.return_value.__enter__.return_value
    connection.dialect.name = "postgresql"
    connection.scalar.return_value = 1
    assert not share_data.import_snapshot(
        tmp_path, tmp_path / "storage", tmp_path / "models", database
    )
    assert not (tmp_path / "storage").exists()


def test_missing_columns_are_rejected_before_import(snapshot):
    path = snapshot / "database.json"
    data = json.loads(path.read_text())
    del data["tables"]["users"][0]["username"]
    path.write_text(json.dumps(data), encoding="utf-8")
    rewrite_manifest(snapshot, data)
    with pytest.raises(ValueError, match="exactly the application columns"):
        share_data.verify_snapshot(snapshot)


def test_seed_uses_bounded_parameterized_batches():
    connection = MagicMock()
    rows = [
        share_data.archived_actor(
            {"id": uuid4(), "created_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}
        )
        for _ in range(401)
    ]
    share_data.insert_seed_rows(connection, share_data.Base.metadata.tables["users"], rows)
    calls = connection.execute.call_args_list
    assert [len(call.args[1]) for call in calls] == [200, 200, 1]
    assert str(calls[0].args[1][0]["id"]) == rows[0]["id"]
    assert calls[0].args[1][0]["is_active"] is False
    connection.execute.reset_mock()
    share_data.insert_seed_rows(connection, share_data.Base.metadata.tables["users"], [])
    connection.execute.assert_not_called()


def test_seed_file_is_complete_before_publication_and_reused_on_retry(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"verified-fixture")
    target = tmp_path / "storage/image.jpg"
    expected = share_data.file_digest(source)
    assert share_data.copy_seed_file(source, target, expected)
    assert target.read_bytes() == source.read_bytes()
    inode = target.stat().st_ino
    assert not share_data.copy_seed_file(source, target, expected)
    assert target.stat().st_ino == inode
    assert not list(target.parent.glob(".seed-*.tmp"))


def test_different_existing_file_is_never_overwritten(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"snapshot")
    target.write_bytes(b"existing-private-data")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        share_data.copy_seed_file(source, target, share_data.file_digest(source))
    assert target.read_bytes() == b"existing-private-data"


def test_existing_directory_is_not_replaced_by_a_file(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"snapshot")
    target.mkdir()
    with pytest.raises(ValueError, match="refusing to overwrite"):
        share_data.copy_seed_file(source, target, share_data.file_digest(source))
    assert target.is_dir()


def test_changed_source_does_not_publish_an_invalid_file(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"original")
    expected = share_data.file_digest(source)
    source.write_bytes(b"changed-after-verification")
    with pytest.raises(ValueError, match="changed during import"):
        share_data.copy_seed_file(source, target, expected)
    assert not target.exists()
    assert not list(tmp_path.glob(".seed-*.tmp"))


@pytest.mark.parametrize("operation", ["fsync", "link"])
def test_copy_error_cleans_its_temporary_file(tmp_path, monkeypatch, operation):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"original")

    def fail(*args):
        raise OSError("simulated-disk-failure")

    monkeypatch.setattr(share_data.os, operation, fail)
    with pytest.raises(OSError):
        share_data.copy_seed_file(source, target, share_data.file_digest(source))
    assert not target.exists()
    assert not list(tmp_path.glob(".seed-*.tmp"))


def test_interrupted_stream_never_leaves_a_partial_target(tmp_path, monkeypatch):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"snapshot")
    expected = share_data.file_digest(source)
    original_open = Path.open
    stream = MagicMock()
    stream.__enter__.return_value.read.side_effect = [b"partial", OSError("interrupted-stream")]

    def open_source(path, *args, **kwargs):
        return stream if path == source else original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_source)
    with pytest.raises(OSError):
        share_data.copy_seed_file(source, target, expected)
    assert not target.exists()
    assert not list(tmp_path.glob(".seed-*.tmp"))


@pytest.mark.parametrize("same_content", [True, False])
def test_racing_file_creation_is_not_overwritten(tmp_path, monkeypatch, same_content):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"snapshot")
    concurrent_content = b"snapshot" if same_content else b"concurrent-data"
    original_link = share_data.os.link

    def race(temporary, destination):
        destination.write_bytes(concurrent_content)
        original_link(temporary, destination)

    monkeypatch.setattr(share_data.os, "link", race)
    if same_content:
        assert not share_data.copy_seed_file(source, target, share_data.file_digest(source))
    else:
        with pytest.raises(ValueError, match="refusing to overwrite"):
            share_data.copy_seed_file(source, target, share_data.file_digest(source))
    assert target.read_bytes() == concurrent_content
    assert not list(tmp_path.glob(".seed-*.tmp"))
