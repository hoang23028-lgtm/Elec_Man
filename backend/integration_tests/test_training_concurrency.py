"""Queue producers must serialize on PostgreSQL, not just in-process mocks."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier

from PIL import Image
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.system_setting import SystemSetting
from app.models.training_run import TrainingRun
from app.services.ai_result_service import store_immutable_ai_result
from app.services.job_service import claim_next_job, mark_job_completed

API = "/api/v1"
POLYGON = {
    "points": [
        {"x": 0.1, "y": 0.1},
        {"x": 0.9, "y": 0.1},
        {"x": 0.9, "y": 0.9},
        {"x": 0.1, "y": 0.9},
    ]
}


def test_simultaneous_training_requests_create_exactly_one_run(login):
    clients = [login("SUPER_ADMIN"), login("SUPER_ADMIN")]
    batch = clients[0].post(API + "/batches", json={"original_folder_name": "training-race"})
    assert batch.status_code == 201
    image_ids = []
    for index in range(3):
        stream = BytesIO()
        Image.new("RGB", (640, 480), (110 + index, 200, 100)).save(stream, "PNG")
        uploaded = clients[0].post(
            API + f"/batches/{batch.json()['id']}/images",
            files={"file": (f"training-{index}.png", stream.getvalue(), "image/png")},
        )
        assert uploaded.status_code == 201
        image_ids.append(uploaded.json()["id"])
    assert clients[0].post(API + f"/batches/{batch.json()['id']}/start").status_code == 200
    with SessionLocal() as db:
        for _ in image_ids:
            job = claim_next_job(db, "training-fixture-worker")
            assert job is not None and str(job.image_id) in image_ids
            result = {
                "model_version": "integration-fixture",
                "customer_id_ai": None,
                "meter_reading_ai": "00120",
                "customer_confidence": 0,
                "meter_confidence": 0.8,
                "detection_confidence": 0.8,
                "image_quality_score": 0.8,
                "final_confidence": 0.8,
                "status": "REVIEW_REQUIRED",
                "processing_time_ms": 1,
            }
            store_immutable_ai_result(db, job.image_id, result)
            db.commit()
            mark_job_completed(db, job.id, result)
    for image_id in image_ids:
        region = clients[0].put(
            API + f"/results/{image_id}/meter-region",
            json={"expected_revision": 1, "meter_polygon": POLYGON},
        )
        assert region.status_code == 200, region.text
        labeled = clients[0].post(
            API + f"/results/{image_id}/training-label",
            json={
                "expected_revision": 2,
                "final_meter_reading": "00120",
                "reading_polygon": POLYGON,
            },
        )
        assert labeled.status_code == 200, labeled.text
        index = image_ids.index(image_id)
        annotated = clients[0].put(
            API + f"/training/data/{image_id}",
            json={
                "expected_revision": 0,
                "expected_label_revision": labeled.json()["revision"],
                "group_key": f"TEST-QUEUE-{index}",
                "partition": "VALIDATION" if index == 2 else "TRAIN",
                "identity_verified": True,
                "label_verified": True,
            },
        )
        assert annotated.status_code == 200, annotated.text
    with SessionLocal() as db:
        settings = db.scalars(
            select(SystemSetting).where(
                SystemSetting.key.in_(("training_auto_start", "training_min_samples"))
            )
        ).all()
        originals = {row.key: row.value_json for row in settings}
        assert len(originals) == 2
        for row in settings:
            row.value_json = 0 if row.key == "training_auto_start" else 3
        db.commit()
    barrier = Barrier(2)
    try:

        def enqueue(index):
            barrier.wait(timeout=10)
            return clients[index].post(API + "/training/runs")

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(enqueue, (0, 1)))
        assert sorted(response.status_code for response in responses) == [202, 409]
        run_id = next(
            response.json()["id"] for response in responses if response.status_code == 202
        )
        with SessionLocal() as db:
            active = db.scalars(select(TrainingRun).where(TrainingRun.status == "PENDING")).all()
            assert len(active) == 1 and str(active[0].id) == run_id
            logs = db.scalars(
                select(AuditLog).where(
                    AuditLog.action == "TRAINING_QUEUED", AuditLog.target_id == run_id
                )
            ).all()
            assert len(logs) == 1
            # This database is disposable and has no trainer. Do not leave an active fixture.
            active[0].status = "FAILED"
            active[0].stage = "FAILED"
            active[0].error_message = "Isolated queue test complete; no model was trained"
            db.commit()
    finally:
        with SessionLocal() as db:
            for row in db.scalars(select(SystemSetting).where(SystemSetting.key.in_(originals))):
                row.value_json = originals[row.key]
            db.commit()
