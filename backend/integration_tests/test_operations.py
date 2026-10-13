"""Real API/auth/SQL/files; OCR output is injected at the worker result boundary."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.models.session import SessionRecord
from app.security.tokens import hash_token
from app.services.ai_result_service import store_immutable_ai_result
from app.services.job_service import claim_next_job, mark_job_completed

API = "/api/v1"
POLYGON = {
    "points": [
        {"x": 0.1, "y": 0.2},
        {"x": 0.8, "y": 0.2},
        {"x": 0.8, "y": 0.6},
        {"x": 0.1, "y": 0.6},
    ]
}


def ok(response, code=200):
    assert response.status_code == code, response.text
    return response.json()


def official_count():
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(ConfirmedMonthlyReading)
            .where(ConfirmedMonthlyReading.customer_code == "PN2.001")
        )


@pytest.mark.parametrize("role", ["VIEWER", "ADMIN", "SUPER_ADMIN"])
def test_real_session_permissions(login, role):
    client = login(role)
    for path in ("/batches", "/customers", "/results"):
        assert client.get(API + path).status_code == (403 if role == "VIEWER" else 200)
    for path in ("/users", "/settings", "/training", "/models", "/audit"):
        response = client.get(API + path)
        assert response.status_code == (200 if role == "SUPER_ADMIN" else 403), response.text
    del client.headers["X-CSRF-Token"]
    assert (
        client.post(API + "/batches", json={"original_folder_name": "blocked"}).status_code == 403
    )


def test_anonymous_cannot_read_operations():
    with TestClient(app) as client:
        assert client.get(API + "/dashboard").status_code == 200
        for path in ("/batches", "/customers", "/results", "/users", "/training"):
            assert client.get(API + path).status_code == 401


def test_logout_revokes_session(login):
    client = login("ADMIN")
    previous_cookies = dict(client.cookies)
    assert client.post(API + "/auth/logout").status_code == 204
    client.cookies.update(previous_cookies)
    assert client.get(API + "/batches").status_code == 401


def test_expired_session_is_rejected(login):
    client = login("ADMIN")
    with SessionLocal() as db:
        session = db.scalar(
            select(SessionRecord).where(
                SessionRecord.session_token_hash == hash_token(client.cookies["ema_session"])
            )
        )
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.get(API + "/batches").status_code == 401


def test_role_change_revokes_existing_session(login):
    system = login("SUPER_ADMIN")
    account = ok(
        system.post(
            API + "/users",
            json={
                "username": "role_change",
                "password": "Integration-test-only-92!",
                "role": "ADMIN",
            },
        ),
        201,
    )
    operator = login("role_change")
    assert operator.get(API + "/batches").status_code == 200
    ok(system.patch(API + f"/users/{account['id']}", json={"role": "VIEWER"}))
    assert operator.get(API + "/batches").status_code == 401
    assert login("role_change").get(API + "/batches").status_code == 403


def test_upload_label_confirm_edit_export_reject_reopen(login):
    client = login("ADMIN")
    ok(
        client.post(
            API + "/customers",
            json={
                "customer_code": "pn2.001",
                "full_name": "Khách kiểm thử",
                "address": "Dữ liệu giả",
                "electricity_route": "TEST",
                "meter_serial": "TEST001",
                "initial_reading": 100,
                "usage_purpose": "Sinh hoạt",
            },
        ),
        201,
    )
    batch = ok(client.post(API + "/batches", json={"original_folder_name": "integration"}), 201)
    upload_url = API + f"/batches/{batch['id']}/images"
    invalid = client.post(upload_url, files={"file": ("fake.png", b"not an image", "image/png")})
    assert invalid.status_code in (400, 415, 422)
    stream = BytesIO()
    Image.new("RGB", (640, 480), "white").save(stream, format="PNG")
    content = stream.getvalue()
    uploaded = ok(client.post(upload_url, files={"file": ("meter.png", content, "image/png")}), 201)
    image_id = uploaded["id"]
    ok(client.post(API + f"/batches/{batch['id']}/start"))
    result = {
        "model_version": "integration-fixture",
        "customer_id_ai": None,
        "meter_reading_ai": "00120",
        "customer_confidence": 0,
        "meter_confidence": 0.99,
        "detection_confidence": 0.99,
        "image_quality_score": 0.99,
        "final_confidence": 0.99,
        "status": "REVIEW_REQUIRED",
        "processing_time_ms": 1,
    }
    with SessionLocal() as db:
        job = claim_next_job(db, "integration-worker")
        assert job is not None and str(job.image_id) == image_id
        store_immutable_ai_result(db, job.image_id, result)
        db.commit()
        mark_job_completed(db, job.id, result)
    assert official_count() == 0
    ok(
        client.post(
            API + f"/results/{image_id}/training-label",
            json={
                "final_meter_reading": "00123",
                "expected_revision": 1,
                "reading_polygon": POLYGON,
            },
        )
    )
    # A fresh authenticated client simulates leaving and returning: labels must persist.
    rows = ok(login("ADMIN").get(API + "/results"))
    row = next(item for item in rows if item["image_id"] == image_id)
    assert row["review_status"] == "LABELED"
    assert row["final_meter_reading"] == "00123"
    assert row["reading_polygon"] == POLYGON
    # A second browser still holding the pre-label revision cannot overwrite it.
    stale_label = client.post(
        API + f"/results/{image_id}/training-label",
        json={
            "expected_revision": 1,
            "final_meter_reading": "00999",
            "reading_polygon": POLYGON,
        },
    )
    assert stale_label.status_code == 412
    assert (
        client.put(
            API + f"/results/{image_id}/meter-region",
            json={
                "expected_revision": 1,
                "meter_polygon": POLYGON,
            },
        ).status_code
        == 412
    )
    assert (
        client.put(
            API + f"/results/{image_id}/review",
            json={
                "expected_revision": 1,
                "action": "REJECT",
            },
        ).status_code
        == 412
    )
    assert (
        client.post(
            API + f"/results/{image_id}/training-label",
            json={
                "final_meter_reading": "00999",
                "reading_polygon": POLYGON,
            },
        ).status_code
        == 422
    )

    assert official_count() == 0
    review_url = API + f"/results/{image_id}/review"
    payload = {
        "expected_revision": row["revision"],
        "action": "CONFIRM",
        "final_customer_id": "PN2.001",
        "final_meter_reading": "00123",
        "reading_month": "2026-10-01",
    }
    missing_month = {key: value for key, value in payload.items() if key != "reading_month"}
    assert client.put(review_url, json=missing_month).status_code == 422
    assert official_count() == 0
    invalid_month = {**payload, "reading_month": "2026-10-12"}
    assert client.put(review_url, json=invalid_month).status_code == 422
    ok(client.put(review_url, json=payload))
    # The now-confirmed record cannot be rejected by an old browser draft.
    assert (
        client.put(
            review_url,
            json={
                "action": "REJECT",
                "expected_revision": payload["expected_revision"],
            },
        ).status_code
        == 412
    )
    with SessionLocal() as db:
        record = db.scalar(select(ConfirmedMonthlyReading))
        assert record.customer_code == "PN2.001"
        assert record.meter_reading == 123
        assert record.image_data == content
    # A second image cannot replace another image's official customer/month record.
    second_batch = ok(
        client.post(API + "/batches", json={"original_folder_name": "duplicate-month"}), 201
    )
    stream = BytesIO()
    Image.new("RGB", (640, 480), "gray").save(stream, format="PNG")
    duplicate = ok(
        client.post(
            API + f"/batches/{second_batch['id']}/images",
            files={
                "file": ("second.png", stream.getvalue(), "image/png"),
            },
        ),
        201,
    )
    ok(client.post(API + f"/batches/{second_batch['id']}/start"))
    with SessionLocal() as db:
        job = claim_next_job(db, "integration-worker")
        assert job is not None and str(job.image_id) == duplicate["id"]
        store_immutable_ai_result(db, job.image_id, result)
        db.commit()
        mark_job_completed(db, job.id, result)
    response = client.put(
        API + f"/results/{duplicate['id']}/review", json={**payload, "expected_revision": 1}
    )
    assert response.status_code == 409, response.text
    assert official_count() == 1
    rows = ok(client.get(API + "/results"))
    duplicate_row = next(item for item in rows if item["image_id"] == duplicate["id"])
    assert duplicate_row["image_status"] == "REVIEW_REQUIRED"
    payload.update(final_meter_reading="00124", reason="Sửa chỉ số kiểm thử")
    payload["expected_revision"] = next(item for item in rows if item["image_id"] == image_id)[
        "revision"
    ]
    ok(client.put(review_url, json=payload))
    with SessionLocal() as db:
        log = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "UPDATE_CONFIRMED_RESULT", AuditLog.target_id == image_id
            )
        )
        assert log.details_json["meter_reading_before"] == "00123"
        assert log.details_json["meter_reading_after"] == "00124"
    bundle = ok(client.post(API + "/exports/final?month=10&year=2026"))
    assert bundle["exported_rows"] == 1
    exported = ok(client.get(bundle["json_download_url"]))
    assert exported[0]["ma_khach_hang"] == "PN2.001"
    assert exported[0]["chi_so_khoi_tao"] == 124
    assert client.get(bundle["excel_download_url"]).content.startswith(b"PK")
    current = next(
        item for item in ok(client.get(API + "/results")) if item["image_id"] == image_id
    )
    ok(
        client.put(
            review_url,
            json={
                "action": "REJECT",
                "reason": "Ảnh kiểm thử",
                "expected_revision": current["revision"],
            },
        )
    )
    assert official_count() == 0
    empty_export = ok(client.post(API + "/exports/final?month=10&year=2026"))
    assert empty_export["exported_rows"] == 0
    assert ok(client.get(empty_export["json_download_url"])) == []
    current = next(
        item for item in ok(client.get(API + "/results")) if item["image_id"] == image_id
    )
    ok(client.put(review_url, json={"action": "REOPEN", "expected_revision": current["revision"]}))
    rows = ok(client.get(API + "/results"))
    row = next(item for item in rows if item["image_id"] == image_id)
    assert row["image_status"] == "REVIEW_REQUIRED"
    assert row["reading_polygon"] == POLYGON
    editors = [login("ADMIN"), login("ADMIN")]
    revision = row["revision"]

    def save_same_image(index):
        return editors[index].post(
            API + f"/results/{image_id}/training-label",
            json={
                "expected_revision": revision,
                "final_meter_reading": f"0012{index + 5}",
                "reading_polygon": POLYGON,
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(save_same_image, (0, 1)))
    assert sorted(response.status_code for response in responses) == [200, 412]
    winner = next(index for index, response in enumerate(responses) if response.status_code == 200)
    current = next(
        item for item in ok(client.get(API + "/results")) if item["image_id"] == image_id
    )
    assert current["final_meter_reading"] == f"0012{winner + 5}"
    assert current["revision"] == revision + 1
