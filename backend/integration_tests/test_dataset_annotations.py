from sqlalchemy import select
from training_fixtures import samples

from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.meter_reading import MeterReading
from app.services.dataset_service import dataset_samples, quality_summary


def payload(**extra):
    return {
        "expected_revision": 0,
        "expected_label_revision": 1,
        "group_key": "CT001",
        "partition": "TRAIN",
        "identity_verified": True,
        "label_verified": True,
        **extra,
    }


def test_annotations_require_system_role_and_csrf(login):
    for role in ("ADMIN", "VIEWER"):
        response = login(role).get("/api/v1/training/data")
        assert response.status_code == 403
        assert login(role).get("/api/v1/training/health").status_code == 403
    client = login("SUPER_ADMIN")
    with SessionLocal() as db:
        image = samples(db)[0]
    client.headers.pop("X-CSRF-Token")
    assert client.put(f"/api/v1/training/data/{image}", json=payload()).status_code == 403


def test_revision_conflicts_holdout_lock_and_before_after_audit(login):
    client = login("SUPER_ADMIN")
    with SessionLocal() as db:
        image = samples(db)[0]
    url = f"/api/v1/training/data/{image}"
    saved = client.put(url, json=payload(partition="HOLDOUT", group_key="LOCK-TEST"))
    assert saved.status_code == 200, saved.text
    assert saved.json()["holdout_locked_at"]
    assert client.put(url, json=payload()).status_code == 409
    assert (
        client.put(
            url, json=payload(expected_revision=1, partition="TRAIN", group_key="LOCK-TEST")
        ).status_code
        == 422
    )
    assert (
        client.put(
            url, json=payload(expected_revision=1, partition="HOLDOUT", group_key="CHANGED")
        ).status_code
        == 422
    )
    with SessionLocal() as db:
        logs = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "DATASET_ANNOTATION_UPDATED", AuditLog.target_id == str(image)
            )
        ).all()
        assert len(logs) == 1
        assert logs[0].details_json["before_values"] == {}
        assert logs[0].details_json["after_values"]["partition"] == "HOLDOUT"
        reading = db.scalar(select(MeterReading).where(MeterReading.image_id == image))
        reading.final_meter_reading = "00121"
        db.commit()
        summary = quality_summary(
            [s for s in dataset_samples(db) if s["image"]["id"] == str(image)]
        )
        assert summary["stale_labels"] == 1 and summary["verified"] == 0
    assert (
        client.put(
            url, json=payload(expected_revision=1, partition="HOLDOUT", group_key="LOCK-TEST")
        ).status_code
        == 409
    )


def test_same_meter_cannot_cross_partitions_and_rollback_is_complete(login):
    client = login("SUPER_ADMIN")
    with SessionLocal() as db:
        a, b = samples(db, 2)
    assert (
        client.put(f"/api/v1/training/data/{a}", json=payload(group_key="SHARED-GROUP")).status_code
        == 200
    )
    refused = client.put(
        f"/api/v1/training/data/{b}", json=payload(group_key="shared-group", partition="VALIDATION")
    )
    assert refused.status_code == 422
    accepted = client.put(
        f"/api/v1/training/data/{b}", json=payload(group_key="OTHER-GROUP", partition="VALIDATION")
    )
    assert accepted.status_code == 200, accepted.text
    response = client.get("/api/v1/training/health")
    assert response.status_code == 200
    assert "database_url" not in response.text and "password" not in response.text
