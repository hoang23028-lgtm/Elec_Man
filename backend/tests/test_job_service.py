from app.services.job_service import should_auto_confirm


def test_uncalibrated_confidence_never_auto_confirms() -> None:
    result = {
        "customer_id_ai": "KH004",
        "meter_reading_ai": "63751.3",
        "final_confidence": 0.9,
    }

    assert should_auto_confirm(result, 0.9) is False
    result["final_confidence"] = 0.9001
    assert should_auto_confirm(result, 0.9) is False
    result["final_confidence"] = 1.0
    assert should_auto_confirm(result, 0.9) is False


def test_processing_preserves_verified_labels(monkeypatch) -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from uuid import uuid4

    from app.models.processing_job import JobStatus
    from app.services import job_service

    db = MagicMock()
    now = datetime.now(UTC)
    image = SimpleNamespace(
        id=uuid4(), batch_id=uuid4(), original_filename="test.jpg", status="REVIEW_REQUIRED"
    )
    job = SimpleNamespace(id=uuid4(), status=JobStatus.PROCESSING, input_json={})
    reading = SimpleNamespace(
        review_status="LABELED",
        final_meter_reading="01234",
        final_customer_id="PN2.001",
        reviewed_by=uuid4(),
        reviewed_at=now,
        customer_match_status="MATCHED",
    )
    before = vars(reading).copy()
    db.execute.return_value.one_or_none.side_effect = [
        (job, image),
        (SimpleNamespace(id=uuid4()), reading),
    ]
    monkeypatch.setattr(job_service, "find_customer", lambda *_: None)
    monkeypatch.setattr(job_service, "get_auto_confirm_threshold", lambda *_: 0.9)
    monkeypatch.setattr(job_service, "refresh_batch_counters", lambda *_: None)
    job_service.mark_job_completed(
        db,
        job.id,
        {"meter_reading_ai": "99999", "customer_id_ai": "WRONG", "final_confidence": 0.99},
    )
    assert vars(reading) == before
    assert image.status == "REVIEW_REQUIRED"
    assert job.result_json["meter_reading_ai"] == "99999"


def test_auto_confirm_requires_both_extracted_values() -> None:
    result = {
        "customer_id_ai": "KH004",
        "meter_reading_ai": None,
        "final_confidence": 0.99,
    }

    assert should_auto_confirm(result, 0.9) is False


def test_auto_confirm_requires_numeric_meter_reading() -> None:
    result = {
        "customer_id_ai": "KH004",
        "meter_reading_ai": "không đọc được",
        "final_confidence": 0.99,
    }

    assert should_auto_confirm(result, 0.9) is False


def test_human_region_recognition_never_auto_confirms() -> None:
    result = {
        "customer_id_ai": "KH004",
        "meter_reading_ai": "63751",
        "final_confidence": 0.99,
        "human_region_requested": True,
    }

    assert should_auto_confirm(result, 0.9) is False
