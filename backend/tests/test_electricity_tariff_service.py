from datetime import date
from decimal import Decimal

import pytest

from app.services.electricity_tariff_service import (
    ADMINISTRATIVE_TARIFFS,
    TIME_OF_USE_TARIFFS,
    calculate_electricity_bill,
    vat_rate_for,
)


def test_residential_350_kwh_matches_reference_workbook() -> None:
    bill = calculate_electricity_bill(Decimal("350"), "SINH_HOAT", date(2026, 9, 1))

    assert bill is not None
    assert bill.energy_charge_before_vat == 907_000
    assert bill.vat_amount == 72_560
    assert bill.total_amount == 979_560
    assert bill.estimated is False


@pytest.mark.parametrize(
    ("purpose", "consumption", "expected_before_vat"),
    [
        ("SAN_XUAT", "100", 198_700),
        ("HO_SAN_XUAT", "100", 198_700),
        ("KINH_DOANH", "100", 315_200),
        ("HO_KINH_DOANH", "100", 315_200),
        ("VIETTEL", "100", 315_200),
        ("TRUONG_HOC_Y_TE", "100", 207_200),
        ("UB_HANH_CHINH", "100", 222_600),
    ],
)
def test_current_customer_purposes_use_low_voltage_normal_rate(
    purpose: str, consumption: str, expected_before_vat: int
) -> None:
    bill = calculate_electricity_bill(Decimal(consumption), purpose, date(2026, 9, 1))

    assert bill is not None
    assert bill.energy_charge_before_vat == expected_before_vat
    assert bill.total_amount == round(expected_before_vat * 1.08)
    assert bill.estimated is True


def test_reference_tariff_tables_include_three_time_bands_and_voltage_levels() -> None:
    assert TIME_OF_USE_TARIFFS["SAN_XUAT"]["22_TO_UNDER_110_KV"] == {
        "NORMAL": 1833,
        "OFF_PEAK": 1190,
        "PEAK": 3398,
    }
    assert TIME_OF_USE_TARIFFS["KINH_DOANH"]["UNDER_6_KV"] == {
        "NORMAL": 3152,
        "OFF_PEAK": 1918,
        "PEAK": 5422,
    }
    assert ADMINISTRATIVE_TARIFFS["TRUONG_HOC_Y_TE"]["UNDER_6_KV"] == 2072


def test_vat_rate_tracks_reduced_vat_period() -> None:
    assert vat_rate_for(date(2025, 6, 30)) == Decimal("0.10")
    assert vat_rate_for(date(2025, 7, 1)) == Decimal("0.08")
    assert vat_rate_for(date(2026, 12, 31)) == Decimal("0.08")
    assert vat_rate_for(date(2027, 1, 1)) == Decimal("0.10")


def test_unknown_purpose_is_not_silently_billed() -> None:
    assert calculate_electricity_bill(Decimal("100"), "KHONG_XAC_DINH", date.today()) is None
