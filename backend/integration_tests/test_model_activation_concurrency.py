from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Barrier

from sqlalchemy import event, select

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models.model_registry import ModelRecord
from app.services.model_registry_service import MODEL_ACTIVATION_LOCK


def test_simultaneous_model_activation_keeps_one_active_model(login):
    clients = [login("SUPER_ADMIN"), login("SUPER_ADMIN")]
    root = get_settings().models_root
    root.mkdir(parents=True, exist_ok=True)
    ids = []
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
                },
            },
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
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
