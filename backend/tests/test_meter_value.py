from decimal import Decimal

import pytest

from app.services.dashboard_service import _amount
from app.services.meter_value import normalize_meter_reading, parse_meter_value


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("05068.4", Decimal("5068")),
        ("63751,250", Decimal("63751")),
        (" 123 ", Decimal("123")),
        (None, None),
        ("12 kWh", None),
        ("-1", None),
        ("1.2345", None),
    ],
)
def test_parse_meter_value(raw: str | None, expected: Decimal | None) -> None:
    assert parse_meter_value(raw) == expected


def test_normalize_meter_reading_discards_fractional_wheel() -> None:
    assert normalize_meter_reading("05068.4") == "05068"
    assert normalize_meter_reading("63751,3") == "63751"


def test_estimated_amount_uses_configured_unit_price() -> None:
    assert _amount(Decimal("0.2"), 2500) == 500
    assert _amount(None, 2500) is None
