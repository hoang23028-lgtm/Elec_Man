from datetime import UTC, datetime

from app.services.export_service import _excel_datetime, _excel_text


def test_excel_datetime_converts_aware_timestamp_to_naive_utc() -> None:
    value = datetime(2026, 9, 18, 8, 30, tzinfo=UTC)
    converted = _excel_datetime(value)
    assert converted == datetime(2026, 9, 18, 8, 30)
    assert converted is not None and converted.tzinfo is None


def test_excel_text_blocks_formula_prefixes() -> None:
    assert _excel_text("=SUM(1,2)") == "'=SUM(1,2)"
