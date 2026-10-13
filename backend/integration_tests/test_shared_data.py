"""Seed data only in disposable PostgreSQL schemas, never application volumes."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.database import engine
from app.models.base import Base
from app.scripts import share_data


@pytest.fixture
def seed_database():
    schema = f"seed_test_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    isolated = engine.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(isolated)
        yield isolated
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))


def create_snapshot(directory, count=601):
    directory.mkdir()
    tables = {table.name: [] for table in share_data.TABLES}
    timestamp = datetime.now(UTC).isoformat()
    for index in range(count):
        tables["customers"].append(
            {
                "id": str(uuid4()),
                "customer_code": f"SEED.{index:04}",
                "lookup_key": f"seed.{index:04}",
                "full_name": f"Khách hàng giả {index}",
                "address": "Địa chỉ thử nghiệm",
                "electricity_route": "Tuyến giả",
                "meter_serial": f"seed-meter-{index}",
                "initial_reading": 123,
                "usage_purpose": "SINH_HOAT",
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
    with engine.connect() as connection:
        migration = connection.scalar(text("SELECT version_num FROM alembic_version"))
    data = {"format": share_data.FORMAT, "migration": migration, "tables": tables}
    share_data.write_json(directory / "database.json", data)
    (directory / "storage").mkdir()
    (directory / "storage/synthetic.txt").write_text("Ảnh thử giả", encoding="utf-8")
    update_snapshot(directory, data)
    return data


def update_snapshot(directory, data):
    (directory / "database.json").write_text(json.dumps(data), encoding="utf-8")
    manifest = {
        "format": share_data.FORMAT,
        "authentication_exported": False,
        "migration": data["migration"],
        "counts": {name: len(rows) for name, rows in data["tables"].items()},
        "files": {
            path.relative_to(directory).as_posix(): {
                "sha256": share_data.file_digest(path),
                "bytes": path.stat().st_size,
            }
            for path in directory.rglob("*")
            if path.is_file() and path.name != "manifest.json"
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def row_count(database, table):
    with database.connect() as connection:
        return connection.scalar(select(func.count()).select_from(Base.metadata.tables[table]))


def test_seed_inserts_customers_in_four_batches_and_skips_missing_payload(seed_database, tmp_path):
    snapshot = tmp_path / "snapshot"
    create_snapshot(snapshot)
    calls = []

    def record(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO") and ".customers " in statement:
            calls.append(statement)

    event.listen(seed_database, "before_cursor_execute", record)
    try:
        assert share_data.import_snapshot(
            snapshot, tmp_path / "storage", tmp_path / "models", seed_database
        )
    finally:
        event.remove(seed_database, "before_cursor_execute", record)
    assert row_count(seed_database, "customers") == 601
    assert len(calls) == 4
    assert not share_data.import_snapshot(
        tmp_path / "missing", tmp_path / "storage", tmp_path / "models", seed_database
    )
    assert row_count(seed_database, "customers") == 601


def test_failed_database_insert_rolls_back_and_retry_reuses_verified_files(seed_database, tmp_path):
    snapshot = tmp_path / "snapshot"
    data = create_snapshot(snapshot)
    data["tables"]["customers"][-1]["customer_code"] = "SEED.0000"
    update_snapshot(snapshot, data)
    settings = Base.metadata.tables["system_settings"]
    with seed_database.begin() as connection:
        connection.execute(
            settings.insert().values(
                key="training_min_samples", value_json=200, description="Default fixture"
            )
        )
    storage, models = tmp_path / "storage", tmp_path / "models"
    with pytest.raises(IntegrityError):
        share_data.import_snapshot(snapshot, storage, models, seed_database)
    assert row_count(seed_database, "customers") == 0
    assert row_count(seed_database, "system_settings") == 1
    existing_file = storage / "synthetic.txt"
    inode = existing_file.stat().st_ino
    assert not list(storage.glob(".seed-*.tmp"))
    data["tables"]["customers"][-1]["customer_code"] = "SEED.0600"
    update_snapshot(snapshot, data)
    assert share_data.import_snapshot(snapshot, storage, models, seed_database)
    assert row_count(seed_database, "customers") == 601
    assert existing_file.stat().st_ino == inode


def test_concurrent_seed_imports_restore_exactly_once(seed_database, tmp_path):
    snapshot = tmp_path / "snapshot"
    create_snapshot(snapshot)
    barrier = Barrier(2)

    def import_once(index):
        barrier.wait(timeout=10)
        return share_data.import_snapshot(
            snapshot, tmp_path / "storage", tmp_path / "models", seed_database
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(import_once, (0, 1)))
    assert sorted(outcomes) == [False, True]
    assert row_count(seed_database, "customers") == 601
    assert not list((tmp_path / "storage").glob(".seed-*.tmp"))


def test_wrong_migration_refuses_fresh_import_before_copying_files(seed_database, tmp_path):
    snapshot = tmp_path / "snapshot"
    data = create_snapshot(snapshot)
    data["migration"] = "different-schema"
    update_snapshot(snapshot, data)
    with pytest.raises(ValueError, match="migration revisions"):
        share_data.import_snapshot(
            snapshot, tmp_path / "storage", tmp_path / "models", seed_database
        )
    assert row_count(seed_database, "customers") == 0
    assert not (tmp_path / "storage").exists()


def test_approved_snapshot_restores_all_relations_labels_and_files(seed_database, tmp_path):
    snapshot = Path(__file__).resolve().parents[2] / "data/snapshot"
    data = share_data.verify_snapshot(snapshot)
    storage, models = tmp_path / "storage", tmp_path / "models"
    assert share_data.import_snapshot(snapshot, storage, models, seed_database)
    for name, rows in data["tables"].items():
        assert row_count(seed_database, name) == len(rows)
    readings = Base.metadata.tables["meter_readings"]
    with seed_database.connect() as connection:
        actual = {row["image_id"]: row for row in connection.execute(select(readings)).mappings()}
    for expected in data["tables"]["meter_readings"]:
        row = actual[UUID(expected["image_id"])]
        for field in ("final_meter_reading", "review_status", "revision"):
            assert row[field] == expected[field]
        for field in ("reading_polygon_json", "meter_polygon_json"):
            assert row[field] == expected[field]
    for prefix, target in (("storage", storage), ("models", models)):
        for source in (snapshot / prefix).rglob("*"):
            if source.is_file():
                restored = target / source.relative_to(snapshot / prefix)
                assert share_data.file_digest(restored) == share_data.file_digest(source)
        assert not list(target.rglob(".seed-*.tmp"))
