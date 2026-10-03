from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.schemas.result import ReadingPolygon
from app.services import region_recognition_service as service


@pytest.mark.parametrize("existing", [False, True])
def test_meter_region_saved_independently_without_changing_reading(existing):
    from app.models.audit_log import AuditLog
    from app.models.meter_reading import MeterReading
    from app.services.review_service import _stored_meter_polygon

    db = MagicMock()
    polygon = ReadingPolygon(
        points=[
            {"x": 0.1, "y": 0.1},
            {"x": 0.8, "y": 0.1},
            {"x": 0.8, "y": 0.8},
            {"x": 0.1, "y": 0.8},
        ]
    )
    image = SimpleNamespace(id=uuid4(), status="REVIEW_REQUIRED", original_filename="test.jpg")
    ai_result = SimpleNamespace(id=uuid4())
    old = MeterReading(final_meter_reading="00123", review_status="LABELED") if existing else None
    db.execute.return_value.one_or_none.return_value = (image, ai_result, old)
    user = SimpleNamespace(id=uuid4())
    saved = service.save_meter_region(db, image.id, polygon, user, None)
    assert _stored_meter_polygon(saved) == polygon
    assert saved.meter_bbox_reviewed_by == user.id
    assert saved.final_meter_reading == ("00123" if existing else None)
    assert saved.review_status == ("LABELED" if existing else "PENDING")
    assert saved.reviewed_by is None
    assert saved.final_customer_id is None
    logs = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], AuditLog)]
    assert logs[0].details_json["meter_polygon_before"] is None
    assert logs[0].details_json["meter_polygon_after"] == polygon.model_dump()
    assert logs[0].action == "SAVE_METER_REGION"
    db.commit.assert_called_once()


@pytest.mark.parametrize("state", ["CONFIRMED", "REJECTED", "PROCESSING"])
def test_meter_region_rejects_non_pending_images(state):
    from fastapi import HTTPException

    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = (SimpleNamespace(status=state), None, None)
    with pytest.raises(HTTPException) as error:
        service.save_meter_region(db, uuid4(), None, None, None)
    assert error.value.status_code == 409
    db.commit.assert_not_called()


def test_meter_region_missing_image():
    from fastapi import HTTPException

    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = None
    with pytest.raises(HTTPException) as error:
        service.save_meter_region(db, uuid4(), None, None, None)
    assert error.value.status_code == 404
    db.commit.assert_not_called()


@pytest.mark.parametrize("include_meter", [False, True])
def test_training_label_can_be_saved_without_customer_or_official_confirmation(include_meter):
    from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
    from app.models.meter_reading import MeterReading

    db = MagicMock()
    polygon = ReadingPolygon(
        points=[
            {"x": 0.1, "y": 0.1},
            {"x": 0.8, "y": 0.1},
            {"x": 0.8, "y": 0.4},
            {"x": 0.1, "y": 0.4},
        ]
    )
    image = SimpleNamespace(id=uuid4(), status="REVIEW_REQUIRED", original_filename="test.jpg")
    ai_result = SimpleNamespace(id=uuid4())
    db.execute.return_value.one_or_none.return_value = (image, ai_result, None)
    user = SimpleNamespace(id=uuid4())
    saved = service.save_training_label(
        db, image.id, "00123", polygon, polygon if include_meter else None, user, None
    )
    assert isinstance(saved, MeterReading)
    assert saved.final_customer_id is None
    assert saved.matched_customer_id is None
    assert saved.final_meter_reading == "00123"
    assert saved.review_status == "LABELED"
    assert saved.reviewed_by == user.id
    assert image.status == "REVIEW_REQUIRED"
    assert not any(
        isinstance(call.args[0], ConfirmedMonthlyReading) for call in db.add.call_args_list
    )
    db.commit.assert_called_once()
    # Omitting the meter outline later must preserve any previously saved outline.
    previous_outline = saved.meter_polygon_json
    db.execute.return_value.one_or_none.return_value = (image, ai_result, saved)
    service.save_training_label(db, image.id, "00124", polygon, None, user, None)
    assert saved.meter_polygon_json == previous_outline


def test_training_request_allows_only_reading_region_and_value():
    from app.schemas.result import TrainingLabelRequest

    request = TrainingLabelRequest.model_validate(
        {
            "final_meter_reading": "00123",
            "reading_polygon": {
                "points": [
                    {"x": 0.1, "y": 0.1},
                    {"x": 0.8, "y": 0.1},
                    {"x": 0.8, "y": 0.4},
                    {"x": 0.1, "y": 0.4},
                ]
            },
        }
    )
    assert request.meter_polygon is None


def test_recognition_request_does_not_replace_saved_training_region(monkeypatch):
    db = MagicMock()
    polygon = ReadingPolygon(
        points=[
            {"x": 0.1, "y": 0.1},
            {"x": 0.8, "y": 0.1},
            {"x": 0.8, "y": 0.4},
            {"x": 0.1, "y": 0.4},
        ]
    )
    image = SimpleNamespace(
        id=uuid4(), batch_id=uuid4(), status="REVIEW_REQUIRED", original_filename="test.jpg"
    )
    ai_result = SimpleNamespace(id=uuid4(), meter_reading_ai="99999")
    reading = SimpleNamespace(
        review_status="LABELED",
        reading_bbox_x=0.2,
        reading_bbox_y=0.2,
        reading_bbox_width=0.5,
        reading_bbox_height=0.2,
        reading_polygon_json={"saved": "gold"},
        final_meter_reading="01234",
    )
    before = vars(reading).copy()
    job = SimpleNamespace(id=uuid4(), status="COMPLETED", priority=0)
    db.execute.return_value.one_or_none.return_value = (image, ai_result, reading, job)
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(max_retry_count=3))
    monkeypatch.setattr(service, "refresh_batch_counters", lambda *_: None)
    service.queue_region_recognition(db, image.id, polygon, SimpleNamespace(id=uuid4()), None)
    assert vars(reading) == before
    assert job.input_json["reading_polygon"] == polygon.model_dump()
    assert job.status == "PENDING"
