from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.confirmed_reading_service import save_confirmed_monthly_reading


def test_review_rejects_non_month_start_date():
    from pydantic import ValidationError

    from app.schemas.result import ReviewRequest

    with pytest.raises(ValidationError):
        ReviewRequest(action="CONFIRM", reading_month="2026-08-15")
    assert ReviewRequest(action="CONFIRM", reading_month="2026-08-01").reading_month == date(
        2026, 8, 1
    )


@pytest.mark.parametrize("selected_month", [None, date(2026, 8, 1)])
def test_edit_retains_official_month_unless_explicitly_changed(
    tmp_path, monkeypatch, selected_month
):
    from app.services import confirmed_reading_service as service

    image_path = tmp_path / "meter.jpg"
    image_path.write_bytes(b"test")
    monkeypatch.setattr(service, "resolve_storage_path", lambda _: image_path)
    db = MagicMock()
    record = SimpleNamespace(
        reading_month=date(2026, 7, 1), source_image_id=uuid4(), meter_reading=100
    )
    db.scalar.side_effect = [record, None]
    image = SimpleNamespace(
        id=record.source_image_id,
        relative_path="meter.jpg",
        original_filename="meter.jpg",
        mime_type="image/jpeg",
        sha256="0" * 64,
    )
    reading = SimpleNamespace(reviewed_at=datetime(2026, 9, 29, tzinfo=UTC), reading_value=200)
    customer = SimpleNamespace(id=uuid4(), customer_code="PN2.001")
    saved, changes = save_confirmed_monthly_reading(
        db, image, reading, customer, uuid4(), selected_month
    )
    assert saved.reading_month == (selected_month or date(2026, 7, 1))
    assert changes["reading_month_before"] == "2026-07-01"


def test_first_confirmation_requires_explicit_month():
    db = MagicMock()
    db.scalar.return_value = None
    reading = SimpleNamespace(reviewed_at=datetime.now(UTC), reading_value=200)
    with pytest.raises(HTTPException) as exc:
        save_confirmed_monthly_reading(
            db, SimpleNamespace(id=uuid4()), reading, SimpleNamespace(id=uuid4()), uuid4()
        )
    assert exc.value.status_code == 422


def test_duplicate_customer_month_does_not_overwrite_another_image():
    db = MagicMock()
    db.scalar.side_effect = [None, SimpleNamespace(source_image_id=uuid4())]
    reading = SimpleNamespace(reviewed_at=datetime.now(UTC), reading_value=200)
    with pytest.raises(HTTPException) as exc:
        save_confirmed_monthly_reading(
            db,
            SimpleNamespace(id=uuid4()),
            reading,
            SimpleNamespace(id=uuid4()),
            uuid4(),
            date(2026, 8, 1),
        )
    assert exc.value.status_code == 409
    db.delete.assert_not_called()
