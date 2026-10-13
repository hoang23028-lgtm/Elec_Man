"""Export approved public business data; seed only a new, empty installation."""

import argparse
import base64
import json
import os
import re
import shutil
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import Date, DateTime, LargeBinary, Numeric, Uuid, delete, func, select, text

from app.core.config import get_settings
from app.core.database import engine
from app.models.base import Base
from app.services.settings_service import RULES

FORMAT = "elec-man-public-snapshot-v1"
SEED_LOCK = 2026101302
TABLES = [table for table in Base.metadata.sorted_tables if table.name != "sessions"]
SECRET_KEY = re.compile(
    r"password|secret|token|csrf|session|cookie|authorization|database_url|dsn|ip_address", re.I
)
SECRET_VALUE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----"
    r"|(?:postgres(?:ql)?(?:\+[\w]+)?|mysql|redis)://[^\s\"']+"
    r"|\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{30,}\b"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bxox[baprs]-[A-Za-z0-9-]{20,}\b"
    r"|\$argon2(?:id|i|d)\$[^\s\"']+|\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}"
)


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items() if not SECRET_KEY.search(key)}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return SECRET_VALUE.sub("[REDACTED]", value) if isinstance(value, str) else value


def encode(value):
    if isinstance(value, bytes | memoryview):
        return {"base64": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, dict | list | str):
        return sanitize(value)
    return value


def archived_actor(row):
    # Foreign keys keep who labeled each image, without exporting login identities/hashes.
    return {
        "id": str(row["id"]),
        "username": f"snapshot_actor_{UUID(str(row['id'])).hex}",
        "password_hash": "!",  # Invalid hash: not an original or usable credential.
        "is_active": False,
        "role": "VIEWER",
        "last_login_at": None,
        "deleted_at": None,
        "created_at": encode(row["created_at"]),
        "updated_at": encode(row["updated_at"]),
    }


def authentication_audit(action):
    return any(
        word in action.upper() for word in ("LOGIN", "LOGOUT", "REGISTER", "USER_", "PASSWORD")
    )


def read_database(connection):
    tables = {}
    for table in TABLES:
        columns = (
            [table.c.id, table.c.created_at, table.c.updated_at]
            if table.name == "users"
            else list(table.columns)
        )
        records = connection.execute(
            select(*columns).order_by(*table.primary_key.columns)
        ).mappings()
        rows = []
        for source in records:
            row = dict(source)
            if table.name == "users":
                row = archived_actor(row)
            elif table.name == "audit_logs":
                if authentication_audit(row["action"]):
                    continue
                row["ip_address"] = None
            elif table.name == "system_settings":
                if row["key"] not in RULES:
                    raise ValueError("Unknown settings must be reviewed before public export")
                if row["key"] == "training_auto_start":
                    row["value_json"] = 0  # Never start an unsolicited training run on a clone.
            if table.name in {"training_runs", "processing_jobs"}:
                row["error_message"] = None
                if row["status"] in {"PENDING", "PROCESSING", "RUNNING"}:
                    row["status"] = "CANCELLED"
            if table.name == "processing_jobs":
                row["worker_id"] = None
            rows.append({key: encode(value) for key, value in row.items()})
        tables[table.name] = rows
    return {
        "format": FORMAT,
        "migration": connection.scalar(text("SELECT version_num FROM alembic_version")),
        "tables": tables,
    }


def file_digest(path):
    result = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def safe_path(root, relative):
    path = PurePosixPath(relative)
    if (
        not relative
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in relative
        or ":" in relative
    ):
        raise ValueError("Unsafe snapshot path")
    candidate = root / relative
    if candidate.is_symlink() or not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError("Linked or escaping snapshot path")
    return candidate


def copy_tree(source, destination):
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source).as_posix()
        safe_path(source, relative)
        if path.is_dir():
            continue
        if (
            not path.is_file()
            or path.name.startswith(".env")
            or path.suffix.lower() in {".pem", ".key", ".log"}
        ):
            raise ValueError("Private or special file found in the data volume")
        if path.stat().st_size >= 100 * 1024**2:
            raise ValueError("Use approved large-file storage for payloads over 100 MiB")
        target = safe_path(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def build_training_data(data, storage, destination):
    from ai.training.dataset import export_sequence_dataset, split_by_meter, split_metadata

    images = {row["id"]: row for row in data["tables"]["images"]}
    rows, annotations, seen = [], [], set()
    destination.mkdir()
    for reading in data["tables"]["meter_readings"]:
        if reading["review_status"] not in {"LABELED", "CONFIRMED"}:
            continue
        image = images[reading["image_id"]]
        annotations.append({"image": image, "label": reading})
        if (
            reading["reviewed_by"]
            and reading["reading_polygon_json"]
            and image["sha256"] not in seen
        ):
            seen.add(image["sha256"])
            rows.append((SimpleNamespace(**image), SimpleNamespace(**reading)))
    with (destination / "labels.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for annotation in annotations:
            stream.write(json.dumps(annotation, ensure_ascii=False, sort_keys=True) + "\n")
    if len(rows) >= 3:
        training, validation = split_by_meter(rows)
        details = export_sequence_dataset(training, validation, storage, destination / "sequence")
        return {"annotations": len(annotations), **details, **split_metadata(rows)}
    return {"annotations": len(annotations), "sequence_exported": False}


def export_snapshot(destination, with_training=False):
    if destination.exists():
        raise ValueError("Choose a new output directory; snapshots are not overwritten")
    settings = get_settings()
    destination.mkdir(parents=True)
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        data = read_database(connection)
    write_json(destination / "database.json", data)
    copy_tree(settings.storage_root, destination / "storage")
    copy_tree(settings.models_root, destination / "models")
    for row in data["tables"]["images"]:
        image = safe_path(destination / "storage", row["relative_path"])
        if file_digest(image) != row["sha256"]:
            raise ValueError("An original image checksum does not match the database")
        safe_path(destination / "storage", row["thumbnail_path"]).resolve(strict=True)
        if row["reviewed_path"]:
            safe_path(destination / "storage", row["reviewed_path"]).resolve(strict=True)
    for row in data["tables"]["models"]:
        if file_digest(safe_path(destination / "models", row["file_path"])) != row["sha256"]:
            raise ValueError("A model checksum does not match the registry")
    training = (
        build_training_data(data, destination / "storage", destination / "training")
        if with_training
        else None
    )
    files = {
        path.relative_to(destination).as_posix(): {
            "sha256": file_digest(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "format": FORMAT,
        "created_at": datetime.now(UTC).isoformat(),
        "public_business_data": True,
        "authentication_exported": False,
        "migration": data["migration"],
        "counts": {name: len(rows) for name, rows in data["tables"].items()},
        "training": training,
        "files": files,
    }
    write_json(destination / "manifest.json", manifest)
    verify_snapshot(destination)
    return manifest


def verify_snapshot(directory):
    manifest = json.loads(safe_path(directory, "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("authentication_exported") is not False:
        raise ValueError("Unexpected snapshot format or authentication payload")
    files = manifest["files"]
    actual = {
        path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file()
    }
    if actual != set(files) | {"manifest.json"}:
        raise ValueError("Unlisted or missing snapshot files")
    for relative, expected in files.items():
        path = safe_path(directory, relative)
        if (
            (
                relative != "database.json"
                and not relative.startswith(("storage/", "models/", "training/"))
            )
            or path.name.startswith(".env")
            or path.suffix.lower() in {".pem", ".key", ".log"}
        ):
            raise ValueError("Private or unexpected file in public snapshot")
        if path.stat().st_size != expected["bytes"] or file_digest(path) != expected["sha256"]:
            raise ValueError("Snapshot payload checksum mismatch")
        if path.suffix in {".json", ".jsonl", ".tsv", ".txt"} and SECRET_VALUE.search(
            path.read_text(encoding="utf-8")
        ):
            raise ValueError("Credential-like content in public snapshot")
    data = json.loads((directory / "database.json").read_text(encoding="utf-8"))
    if data.get("format") != FORMAT or set(data["tables"]) != {table.name for table in TABLES}:
        raise ValueError("Unexpected table set; authentication sessions must be absent")
    if data["migration"] != manifest["migration"]:
        raise ValueError("Snapshot migration metadata mismatch")
    for name, rows in data["tables"].items():
        if len(rows) != manifest["counts"][name]:
            raise ValueError("Snapshot row count mismatch")
    for actor in data["tables"]["users"]:
        if (
            actor["password_hash"] != "!"
            or actor["is_active"] is not False
            or actor["role"] != "VIEWER"
            or actor["username"] != f"snapshot_actor_{UUID(actor['id']).hex}"
        ):
            raise ValueError("Public snapshots cannot contain usable accounts")
    for row in data["tables"]["images"]:
        if file_digest(safe_path(directory / "storage", row["relative_path"])) != row["sha256"]:
            raise ValueError("Original image does not match its label metadata")
        safe_path(directory / "storage", row["thumbnail_path"]).resolve(strict=True)
        if row["reviewed_path"]:
            safe_path(directory / "storage", row["reviewed_path"]).resolve(strict=True)
    for row in data["tables"]["models"]:
        if file_digest(safe_path(directory / "models", row["file_path"])) != row["sha256"]:
            raise ValueError("Model does not match its registry checksum")
    return data


def decode_row(table, row):
    if set(row) - set(table.columns.keys()):
        raise ValueError("Snapshot column is not part of the application schema")
    decoded = {}
    for key, value in row.items():
        kind = table.c[key].type
        if value is not None:
            if isinstance(kind, DateTime):
                value = datetime.fromisoformat(value)
            elif isinstance(kind, Date):
                value = date.fromisoformat(value)
            elif isinstance(kind, Uuid):
                value = UUID(value)
            elif isinstance(kind, Numeric):
                value = Decimal(value)
            elif isinstance(kind, LargeBinary):
                value = base64.b64decode(value["base64"], validate=True)
        decoded[key] = value
    return decoded


def import_snapshot(directory, storage, models, database_engine=engine):
    data = verify_snapshot(directory)
    with database_engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SEED_LOCK})
        if any(
            connection.scalar(select(func.count()).select_from(table))
            for table in TABLES
            if table.name != "system_settings"
        ):
            return False  # An existing account, label or customer is never overwritten.
        if connection.scalar(text("SELECT version_num FROM alembic_version")) != data["migration"]:
            raise ValueError("Snapshot and database migration revisions must match")
        for prefix, target_root in (("storage", storage), ("models", models)):
            source = directory / prefix
            for path in sorted(source.rglob("*")):
                if not path.is_file():
                    continue
                target = safe_path(target_root, path.relative_to(source).as_posix())
                if target.exists():
                    if not target.is_file() or file_digest(target) != file_digest(path):
                        raise ValueError("Existing data file differs; refusing to overwrite")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with path.open("rb") as incoming, target.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
        connection.execute(delete(Base.metadata.tables["system_settings"]))
        for table in TABLES:
            for row in data["tables"][table.name]:
                connection.execute(table.insert().values(**decode_row(table, row)))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "verify", "import"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--with-training", action="store_true")
    args = parser.parse_args()
    if args.action == "export":
        manifest = export_snapshot(args.directory, args.with_training)
        print(json.dumps({"counts": manifest["counts"], "training": manifest["training"]}))
    elif args.action == "verify":
        verify_snapshot(args.directory)
        print("Public data snapshot verified; no authentication sessions or usable accounts.")
    elif os.environ.get("IMPORT_SHARED_DATA", "true").lower() in {"0", "false", "no"}:
        print("Shared data import disabled; kept database as configured.")
    else:
        settings = get_settings()
        imported = import_snapshot(args.directory, settings.storage_root, settings.models_root)
        print(
            "Imported shared business data."
            if imported
            else "Kept existing database; no shared data overwritten."
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Shared data operation failed ({type(error).__name__}); check private diagnostics.")
        raise SystemExit(2) from None
