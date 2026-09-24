from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

MONEY_UNIT = Decimal("1")
REDUCED_VAT_START = date(2025, 7, 1)
REDUCED_VAT_END = date(2026, 12, 31)

RESIDENTIAL_TIERS = (
    (Decimal("50"), Decimal("1984")),
    (Decimal("50"), Decimal("2050")),
    (Decimal("100"), Decimal("2380")),
    (Decimal("100"), Decimal("2998")),
    (Decimal("100"), Decimal("3350")),
    (None, Decimal("3460")),
)

TIME_OF_USE_TARIFFS = {
    "SAN_XUAT": {
        "AT_LEAST_110_KV": {"NORMAL": 1811, "OFF_PEAK": 1146, "PEAK": 3266},
        "22_TO_UNDER_110_KV": {"NORMAL": 1833, "OFF_PEAK": 1190, "PEAK": 3398},
        "6_TO_UNDER_22_KV": {"NORMAL": 1899, "OFF_PEAK": 1234, "PEAK": 3508},
        "UNDER_6_KV": {"NORMAL": 1987, "OFF_PEAK": 1300, "PEAK": 3640},
    },
    "KINH_DOANH": {
        "AT_LEAST_22_KV": {"NORMAL": 2887, "OFF_PEAK": 1609, "PEAK": 5025},
        "6_TO_UNDER_22_KV": {"NORMAL": 3108, "OFF_PEAK": 1829, "PEAK": 5202},
        "UNDER_6_KV": {"NORMAL": 3152, "OFF_PEAK": 1918, "PEAK": 5422},
    },
}

ADMINISTRATIVE_TARIFFS = {
    "TRUONG_HOC_Y_TE": {"AT_LEAST_6_KV": 1940, "UNDER_6_KV": 2072},
    "UB_HANH_CHINH": {"AT_LEAST_6_KV": 2138, "UNDER_6_KV": 2226},
}


@dataclass(frozen=True)
class ElectricityBill:
    energy_charge_before_vat: int
    vat_amount: int
    total_amount: int
    vat_rate: Decimal
    tariff_label: str
    estimated: bool


def vat_rate_for(reading_at: date | datetime) -> Decimal:
    effective_date = reading_at.date() if isinstance(reading_at, datetime) else reading_at
    return (
        Decimal("0.08")
        if REDUCED_VAT_START <= effective_date <= REDUCED_VAT_END
        else Decimal("0.10")
    )


def _round_money(value: Decimal) -> int:
    return int(value.quantize(MONEY_UNIT, rounding=ROUND_HALF_UP))


def _residential_charge(consumption: Decimal) -> Decimal:
    remaining = consumption
    charge = Decimal("0")
    for allowance, price in RESIDENTIAL_TIERS:
        quantity = remaining if allowance is None else min(remaining, allowance)
        charge += quantity * price
        remaining -= quantity
        if remaining <= 0:
            break
    return charge


def _purpose_tariff(usage_purpose: str) -> tuple[str, int] | None:
    purpose = usage_purpose.strip().upper()
    if purpose in {"HO_SAN_XUAT", "SAN_XUAT"}:
        return "Sản xuất dưới 6 kV, giờ bình thường", 1987
    if purpose in {"HO_KINH_DOANH", "KINH_DOANH", "VIETTEL"}:
        return "Kinh doanh dưới 6 kV, giờ bình thường", 3152
    if purpose == "TRUONG_HOC_Y_TE":
        return "Trường học/Y tế dưới 6 kV", 2072
    if purpose == "UB_HANH_CHINH":
        return "Hành chính sự nghiệp dưới 6 kV", 2226
    return None


def calculate_electricity_bill(
    consumption_kwh: Decimal,
    usage_purpose: str,
    reading_at: date | datetime,
) -> ElectricityBill | None:
    if consumption_kwh < 0:
        return None
    purpose = usage_purpose.strip().upper()
    if purpose == "SINH_HOAT":
        energy_charge = _residential_charge(consumption_kwh)
        tariff_label = "Sinh hoạt lũy tiến 6 bậc"
        estimated = False
    else:
        tariff = _purpose_tariff(purpose)
        if tariff is None:
            return None
        tariff_label, unit_price = tariff
        energy_charge = consumption_kwh * Decimal(unit_price)
        estimated = True

    rounded_energy = _round_money(energy_charge)
    vat_rate = vat_rate_for(reading_at)
    vat_amount = _round_money(Decimal(rounded_energy) * vat_rate)
    return ElectricityBill(
        energy_charge_before_vat=rounded_energy,
        vat_amount=vat_amount,
        total_amount=rounded_energy + vat_amount,
        vat_rate=vat_rate,
        tariff_label=tariff_label,
        estimated=estimated,
    )
