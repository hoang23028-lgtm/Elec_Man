from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, literal, select

from app.services.billing_query import bill_amounts
from app.services.electricity_tariff_service import calculate_electricity_bill


@pytest.mark.parametrize(
    "purpose",
    [
        "SINH_HOAT",
        "HO_SAN_XUAT",
        "KINH_DOANH",
        "VIETTEL",
        "TRUONG_HOC_Y_TE",
        "UB_HANH_CHINH",
        "UNKNOWN",
    ],
)
@pytest.mark.parametrize("quantity", [-1, 0, 50, 51, 100, 101, 200, 301, 400, 10000])
@pytest.mark.parametrize(
    "month",
    [
        date(2023, 12, 1),
        date(2024, 12, 1),
        date(2025, 4, 1),
        date(2025, 5, 1),
        date(2025, 6, 1),
        date(2025, 7, 1),
        date(2026, 12, 1),
        date(2027, 1, 1),
    ],
)
def test_sql_totals_match_detail_calculator(purpose, quantity, month):
    engine = create_engine("sqlite://")
    energy, vat = bill_amounts(literal(Decimal(quantity)), literal(purpose), literal(month))
    with engine.connect() as connection:
        actual = connection.execute(select(energy, vat)).one()
    expected = calculate_electricity_bill(Decimal(quantity), purpose, month)
    assert tuple(actual) == (
        (expected.energy_charge_before_vat, expected.vat_amount) if expected else (None, None)
    )
    engine.dispose()


@pytest.mark.parametrize(
    "previous,current,expected",
    [
        (date(2026, 1, 1), date(2026, 2, 1), 100),
        (date(2026, 1, 1), date(2026, 3, 1), None),
        (date(2025, 12, 1), date(2026, 1, 1), 100),
    ],
)
def test_missing_month_is_not_charged_as_one_month(previous, current, expected):
    from app.services.dashboard_service import _consumption

    source = select(
        literal(previous).label("previous_month"),
        literal(current).label("reading_month"),
        literal(100).label("previous_value"),
        literal(0).label("initial_value"),
        literal(200).label("current_value"),
    ).cte()
    with create_engine("sqlite://").connect() as connection:
        assert connection.scalar(select(_consumption(source))) == expected
