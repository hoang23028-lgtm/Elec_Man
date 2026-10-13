from datetime import date
from decimal import Decimal

import pytest

from app.services.electricity_billing_policy import TARIFF_VERSIONS, billing_unavailable_reason
from app.services.electricity_tariff_service import calculate_electricity_bill, vat_rate_for


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


def test_versions_cover_the_verified_low_voltage_rates() -> None:
    old, current = TARIFF_VERSIONS
    assert old.residential_prices == (1893, 1956, 2271, 2860, 3197, 3302)
    assert current.residential_prices == (1984, 2050, 2380, 2998, 3350, 3460)
    assert old.flat_tariff("HO_SAN_XUAT")[1] == 1896
    assert old.flat_tariff("VIETTEL")[1] == 3007
    assert old.flat_tariff("TRUONG_HOC_Y_TE")[1] == 1977
    assert old.flat_tariff("UB_HANH_CHINH")[1] == 2124
    assert current.flat_tariff("TRUONG_HOC_Y_TE")[1] == 2072


def test_vat_rate_tracks_reduced_vat_period() -> None:
    assert vat_rate_for(date(2024, 12, 31)) is None
    assert vat_rate_for(date(2025, 1, 1)) == Decimal("0.08")
    assert vat_rate_for(date(2025, 6, 30)) == Decimal("0.08")
    assert vat_rate_for(date(2025, 7, 1)) == Decimal("0.08")
    assert vat_rate_for(date(2026, 12, 31)) == Decimal("0.08")
    assert vat_rate_for(date(2027, 1, 1)) == Decimal("0.10")


def test_unknown_purpose_is_not_silently_billed() -> None:
    assert calculate_electricity_bill(Decimal("100"), "KHONG_XAC_DINH", date.today()) is None


def test_historical_bill_uses_old_price_not_confirmation_date() -> None:
    bill = calculate_electricity_bill(Decimal(100), "SINH_HOAT", date(2025, 4, 1))
    assert bill.energy_charge_before_vat == 192450
    assert bill.vat_amount == 15396
    assert bill.tariff_version == "2699/QĐ-BCT"
    assert bill.vat_policy == "180/2024/NĐ-CP"


@pytest.mark.parametrize("month", [date(2025, 5, 1), date(2025, 5, 10), date(2025, 5, 31)])
def test_mid_month_change_requires_allocation_data(month) -> None:
    assert calculate_electricity_bill(Decimal(100), "SINH_HOAT", month) is None
    assert "đổi giá giữa kỳ" in billing_unavailable_reason(Decimal(100), "SINH_HOAT", month)


def test_current_version_retains_pre_july_reduced_vat() -> None:
    bill = calculate_electricity_bill(Decimal(100), "SINH_HOAT", date(2025, 6, 1))
    assert bill.energy_charge_before_vat == 201700
    assert bill.vat_amount == 16136
    assert bill.tariff_version == "1279/QĐ-BCT"
    assert bill.vat_policy == "180/2024/NĐ-CP"
    assert (
        calculate_electricity_bill(Decimal(100), "SINH_HOAT", date(2025, 7, 1)).vat_policy
        == "204/2025/QH15"
    )


@pytest.mark.parametrize(
    "month,reason",
    [
        (date(2023, 12, 1), "biểu giá"),
        (date(2024, 12, 1), "VAT"),
    ],
)
def test_unverified_history_is_not_silently_priced(month, reason) -> None:
    assert calculate_electricity_bill(Decimal(100), "SINH_HOAT", month) is None
    assert reason in billing_unavailable_reason(Decimal(100), "SINH_HOAT", month)


@pytest.mark.parametrize("quantity", ["-1", "NaN", "Infinity", "-Infinity"])
def test_invalid_consumption_is_not_billed(quantity) -> None:
    assert calculate_electricity_bill(Decimal(quantity), "SINH_HOAT", date(2026, 1, 1)) is None
