from types import SimpleNamespace

from app.services.review_service import _normalized_ai_reading_bbox, get_result_status_counts


def test_operations_status_counts_share_the_queue_invariants() -> None:
    from unittest.mock import MagicMock

    db = MagicMock()
    db.execute.return_value.one.return_value = SimpleNamespace(
        review_required=37,
        pending=0,
        labeled=37,
        confirmed=0,
        rejected=24,
    )

    counts = get_result_status_counts(db)

    assert counts.model_dump() == {
        "review_required": 37,
        "pending": 0,
        "labeled": 37,
        "confirmed": 0,
        "rejected": 24,
    }
    sql = str(db.execute.call_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "images.status = 'REVIEW_REQUIRED'" in sql
    assert "coalesce(meter_readings.review_status, 'PENDING') = 'LABELED'" in sql
    assert "images.status = 'CONFIRMED'" in sql
    assert "images.status = 'REJECTED'" in sql


def test_confirmation_saves_meter_polygon_and_before_after_log_atomically(monkeypatch):
    from datetime import date
    from unittest.mock import MagicMock
    from uuid import uuid4

    from app.models.audit_log import AuditLog
    from app.models.manual_correction import ManualCorrection
    from app.models.meter_reading import MeterReading
    from app.schemas.result import ReviewRequest
    from app.services import review_service as service

    image = SimpleNamespace(id=uuid4(), batch_id=uuid4(), original_filename="meter.jpg")
    ai_result = SimpleNamespace(id=uuid4(), customer_id_ai="PN2.001", meter_reading_ai="01234")
    user = SimpleNamespace(id=uuid4())
    customer = SimpleNamespace(id=uuid4(), customer_code="PN2.001")
    reading = MeterReading(
        image_id=image.id,
        ai_result_id=ai_result.id,
        review_status="LABELED",
        final_customer_id=None,
        final_meter_reading="01234",
    )
    polygon = {
        "points": [
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.9, "y": 0.9},
            {"x": 0.1, "y": 0.9},
        ]
    }
    payload = ReviewRequest(
        action="CONFIRM",
        final_customer_id="PN2.001",
        final_meter_reading="01234",
        reading_month="2026-09-01",
        meter_polygon=polygon,
    )
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = (image, ai_result, reading)
    monkeypatch.setattr(service, "find_customer", lambda *_: customer)
    monkeypatch.setattr(service, "apply_customer_match", lambda *_: None)
    monkeypatch.setattr(service, "archive_reviewed_image", lambda *_: "confirmed/PN2.001.jpg")
    monkeypatch.setattr(service, "refresh_batch_counters", lambda *_: None)

    def save_official(*_):
        # Both geometry and official values must be present before official persistence.
        assert reading.meter_polygon_json == polygon
        assert reading.final_meter_reading == "01234"
        db.commit.assert_not_called()
        return SimpleNamespace(id=uuid4(), reading_month=date(2026, 9, 1)), {}

    monkeypatch.setattr(service, "save_confirmed_monthly_reading", save_official)
    service.review_result(db, image.id, payload, user, "127.0.0.1")
    assert reading.meter_bbox_reviewed_by == user.id
    assert reading.meter_bbox_width == 0.8
    added = [call.args[0] for call in db.add.call_args_list]
    correction = next(
        item
        for item in added
        if isinstance(item, ManualCorrection) and item.field_name == "meter_polygon"
    )
    assert correction.old_value == "null"
    log = next(item for item in added if isinstance(item, AuditLog))
    assert log.details_json["meter_polygon_before"] is None
    assert log.details_json["meter_polygon_after"] == polygon
    assert "meter_polygon" in log.details_json["changed_fields"]
    db.commit.assert_called_once()


def test_ai_reading_region_is_normalized_after_preprocessing_resize() -> None:
    image = SimpleNamespace(width=3200, height=1600)
    ai_result = SimpleNamespace(raw_result_json={"regions": {"reading": [400, 200, 800, 300]}})

    bbox = _normalized_ai_reading_bbox(image, ai_result)

    assert bbox is not None
    assert bbox.model_dump() == {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.375}
