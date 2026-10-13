from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier

from PIL import Image
from sqlalchemy import event, select

from app.core.database import SessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.services.ai_result_service import store_immutable_ai_result
from app.services.job_service import claim_next_job, mark_job_completed

API = "/api/v1"


def ok(response, code=200):
    assert response.status_code == code, response.text
    return response.json()


def test_concurrent_confirmation_returns_conflict_without_partial_writes(login):
    clients = [login("ADMIN"), login("ADMIN")]
    customer = ok(
        clients[0].post(
            API + "/customers",
            json={
                "customer_code": "RACE.001",
                "full_name": "Concurrency test",
                "address": "Test only",
                "electricity_route": "TEST",
                "meter_serial": "RACE001",
                "initial_reading": 100,
                "usage_purpose": "Sinh hoạt",
            },
        ),
        201,
    )
    batch = ok(clients[0].post(API + "/batches", json={"original_folder_name": "race"}), 201)
    image_ids = []
    for color in ("red", "blue"):
        stream = BytesIO()
        Image.new("RGB", (640, 480), color).save(stream, format="PNG")
        uploaded = ok(
            clients[0].post(
                API + f"/batches/{batch['id']}/images",
                files={
                    "file": (color + ".png", stream.getvalue(), "image/png"),
                },
            ),
            201,
        )
        image_ids.append(uploaded["id"])
    ok(clients[0].post(API + f"/batches/{batch['id']}/start"))
    with SessionLocal() as db:
        for _ in image_ids:
            job = claim_next_job(db, "race-worker")
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
    barrier = Barrier(2)

    def synchronize_inserts(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO confirmed_monthly_readings"):
            barrier.wait(timeout=15)

    def confirm(index):
        return clients[index].put(
            API + f"/results/{image_ids[index]}/review",
            json={
                "action": "CONFIRM",
                "expected_revision": 1,
                "final_customer_id": customer["customer_code"],
                "final_meter_reading": "00123",
                "reading_month": "2026-10-01",
            },
        )

    event.listen(engine, "before_cursor_execute", synchronize_inserts)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(confirm, (0, 1)))
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_inserts)
    assert sorted(response.status_code for response in responses) == [200, 409]
    rows = ok(clients[0].get(API + "/results"))
    for index, response in enumerate(responses):
        row = next(item for item in rows if item["image_id"] == image_ids[index])
        assert row["image_status"] == (
            "CONFIRMED" if response.status_code == 200 else "REVIEW_REQUIRED"
        )
        if response.status_code == 409:
            assert row["final_meter_reading"] == "00120"
            assert row["final_customer_id"] is None
            with SessionLocal() as db:
                assert (
                    db.scalar(
                        select(AuditLog).where(
                            AuditLog.target_id == image_ids[index],
                            AuditLog.action == "CONFIRM_RESULT",
                        )
                    )
                    is None
                )
    with SessionLocal() as db:
        records = db.scalars(
            select(ConfirmedMonthlyReading).where(
                ConfirmedMonthlyReading.customer_code == "RACE.001"
            )
        ).all()
        assert len(records) == 1
    winner = next(index for index, response in enumerate(responses) if response.status_code == 200)
    ok(
        clients[winner].put(
            API + f"/results/{image_ids[winner]}/review",
            json={
                "action": "REJECT",
                "expected_revision": 2,
                "reason": "Cleanup isolated concurrency fixture",
            },
        )
    )
