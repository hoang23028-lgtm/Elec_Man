from datetime import UTC, datetime

from app.services.confirmed_reading_service import reading_month


def test_reading_month_uses_vietnam_confirmation_date() -> None:
    assert reading_month(datetime(2026, 9, 30, 18, 30, tzinfo=UTC)).isoformat() == "2026-10-01"
