from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from threading import Barrier
from uuid import UUID

from sqlalchemy import event, select
from training_fixtures import samples

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models.model_registry import ModelRecord
from app.models.training_run import TrainingRun
from app.services.dataset_policy import make_manifest
from app.services.dataset_service import dataset_samples
from app.services.model_registry_service import MODEL_ACTIVATION_LOCK


def test_simultaneous_model_activation_keeps_one_active_model(login):
    clients = [login("SUPER_ADMIN"), login("SUPER_ADMIN")]
    root = get_settings().models_root
    root.mkdir(parents=True, exist_ok=True)
    ids = []
    with SessionLocal() as db:
        sample_ids = set(str(value) for value in samples(db, 30, "HOLDOUT"))
        snapshot = make_manifest([s for s in dataset_samples(db) if s["image"]["id"] in sample_ids])
    for index in range(2):
        # Registry/API test only; no worker loads these disposable fixture files.
        content = f"Registry fixture {index}, not an inference model".encode()
        (root / f"activation-{index}.npz").write_bytes(content)
        response = clients[index].post(
            "/api/v1/models",
            json={
                "model_name": "isolated-activation",
                "model_type": "reading_region_ridge",
                "version": f"v{index}",
                "file_path": f"activation-{index}.npz",
                "sha256": sha256(content).hexdigest(),
                "metrics": {
                    "validation_groups_verified": True,
                    "validation_images": 30,
                    "validation_region_accuracy": 0.9,
                    "holdout_images": 30,
                    "independent_holdout": True,
                    "end_to_end_evaluated": True,
                    "holdout_end_to_end": {"reading_mean_iou": 0.9},
                },
            },
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
        # Model registration alone cannot activate; attach trusted trainer provenance
        # directly as a disposable DB fixture (never claiming ML quality).
        with SessionLocal() as db:
            record = db.get(ModelRecord, UUID(ids[-1]))
            run = TrainingRun(
                status="COMPLETED",
                trigger="MANUAL",
                stage="COMPLETED",
                progress=100,
                sample_count=0,
                created_at=datetime.now(UTC),
                dataset_hash=snapshot["sha256"],
                metrics_json={
                    "artifact_ids": [str(record.id)],
                    "artifact_sha256": {str(record.id): record.sha256},
                    "dataset_snapshot": snapshot,
                },
            )
            db.add(run)
            db.flush()
            record.metrics_json = {
                **record.metrics_json,
                "training_run_id": str(run.id),
                "dataset_hash": snapshot["sha256"],
            }
            db.commit()
    barrier = Barrier(2)
    lock_calls = []

    def before_lock(conn, cursor, statement, parameters, context, executemany):
        if "pg_advisory_xact_lock" in statement and parameters.get("key") == MODEL_ACTIVATION_LOCK:
            lock_calls.append(True)
            barrier.wait(timeout=10)

    def activate(index):
        return clients[index].put(f"/api/v1/models/{ids[index]}/activate")

    event.listen(engine, "before_cursor_execute", before_lock)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(activate, (0, 1)))
    finally:
        event.remove(engine, "before_cursor_execute", before_lock)
    assert [response.status_code for response in responses] == [200, 200]
    assert len(lock_calls) == 2
    with SessionLocal() as db:
        active = db.scalars(
            select(ModelRecord).where(
                ModelRecord.model_type == "reading_region_ridge", ModelRecord.status == "ACTIVE"
            )
        ).all()
        assert len(active) == 1 and str(active[0].id) in ids
        rows = db.scalars(
            select(ModelRecord).where(ModelRecord.model_name == "isolated-activation")
        ).all()
        assert sorted(row.status for row in rows) == ["ACTIVE", "ARCHIVED"]
        for row in rows:
            row.status = "ARCHIVED"
        db.commit()


def test_architecture_switch_archives_incompatible_regions_and_reader(login):
    # Registry fixtures only, never loaded for inference and never real ML scores.
    client = login("SUPER_ADMIN")
    root = get_settings().models_root
    root.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        sample_ids = {str(value) for value in samples(db, 30, "HOLDOUT")}
        snapshot = make_manifest([s for s in dataset_samples(db) if s["image"]["id"] in sample_ids])
        ids = {}
        for kind in (
            "meter_locator_ridge",
            "reading_region_ridge",
            "parseq_tiny_finetuned",
            "meter_locator_mobilenetv3",
            "reading_region_mobilenetv3",
        ):
            content = f"Non-inference architecture-switch fixture: {kind}".encode()
            path = f"switch-{kind}.fixture"
            (root / path).write_bytes(content)
            record = ModelRecord(
                model_name=f"switch-{kind}",
                model_type=kind,
                version="architecture-switch-v1",
                file_path=path,
                sha256=sha256(content).hexdigest(),
                status="TESTING",
                created_at=datetime.now(UTC),
                metrics_json={
                    "coordinate_space": "meter",
                    "locator_family": "mobilenetv3" if kind.endswith("mobilenetv3") else "ridge",
                    "validation_groups_verified": True,
                    "validation_images": 30,
                    "validation_region_accuracy": 0.95,
                    "validation_meter_region_accuracy": 0.95,
                    "holdout_images": 30,
                    "independent_holdout": True,
                    "end_to_end_evaluated": True,
                    "holdout_reader": {"exact_accuracy": 0.96, "coverage": 1},
                    "holdout_end_to_end": {
                        "meter_mean_iou": 0.9,
                        "reading_mean_iou": 0.9,
                        "exact_accuracy": 0.91,
                        "coverage": 1,
                    },
                    "locator_benchmark": {
                        "independent_holdout": True,
                        "ridge_end_to_end": {
                            "evaluation_complete": True,
                            "meter_mean_iou": 0.81,
                            "reading_mean_iou": 0.81,
                            "exact_accuracy": 0.9,
                            "coverage": 1,
                        },
                    },
                },
            )
            db.add(record)
            db.flush()
            ids[kind] = record.id
        run = TrainingRun(
            status="COMPLETED",
            trigger="MANUAL",
            stage="COMPLETED",
            progress=100,
            created_at=datetime.now(UTC),
            sample_count=0,
            dataset_hash=snapshot["sha256"],
            metrics_json={
                "dataset_snapshot": snapshot,
                "artifact_ids": [str(i) for i in ids.values()],
                "artifact_sha256": {str(i): db.get(ModelRecord, i).sha256 for i in ids.values()},
            },
        )
        db.add(run)
        db.flush()
        for identifier in ids.values():
            record = db.get(ModelRecord, identifier)
            record.metrics_json = {
                **record.metrics_json,
                "training_run_id": str(run.id),
                "dataset_hash": snapshot["sha256"],
            }
        db.commit()

    def activate(kind):
        return client.put(f"/api/v1/models/{ids[kind]}/activate")

    for kind in ("meter_locator_ridge", "reading_region_ridge", "parseq_tiny_finetuned"):
        response = activate(kind)
        assert response.status_code == 200, response.text
    assert activate("reading_region_mobilenetv3").status_code == 422
    assert activate("meter_locator_mobilenetv3").status_code == 200
    assert activate("parseq_tiny_finetuned").status_code == 422
    assert activate("reading_region_mobilenetv3").status_code == 200
    with SessionLocal() as db:
        records = db.scalars(select(ModelRecord).where(ModelRecord.id.in_(ids.values()))).all()
        assert {r.model_type for r in records if r.status == "ACTIVE"} == {
            "meter_locator_mobilenetv3",
            "reading_region_mobilenetv3",
        }
        for record in records:
            record.status = "ARCHIVED"
        db.commit()
