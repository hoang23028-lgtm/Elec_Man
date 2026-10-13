from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.services.electricity_billing_policy import (
    TariffVersion,
    billing_unavailable_reason,
    normalize_purpose,
    tariff_for_month,
    vat_for_month,
)

MONEY_UNIT = Decimal("1")


@dataclass(frozen=True)
class ElectricityBill:
    energy_charge_before_vat: int
    vat_amount: int
    total_amount: int
    vat_rate: Decimal
    tariff_label: str
    estimated: bool
    tariff_version: str
    tariff_source_url: str
    vat_policy: str
    vat_source_url: str


def vat_rate_for(reading_at: date | datetime) -> Decimal | None:
    version = vat_for_month(reading_at)
    return version.rate if version else None


def _round_money(value: Decimal) -> int:
    return int(value.quantize(MONEY_UNIT, rounding=ROUND_HALF_UP))


def _residential_charge(consumption: Decimal, tariff: TariffVersion) -> Decimal:
    remaining = consumption
    charge = Decimal("0")
    for allowance, price in tariff.residential_tiers:
        quantity = remaining if allowance is None else min(remaining, allowance)
        charge += quantity * price
        remaining -= quantity
        if remaining <= 0:
            break
    return charge


def calculate_electricity_bill(
    consumption_kwh: Decimal,
    usage_purpose: str,
    reading_at: date | datetime,
) -> ElectricityBill | None:
    """Estimate one calendar month's bill, refusing unresolved tariff transitions."""
    if billing_unavailable_reason(consumption_kwh, usage_purpose, reading_at):
        return None
    tariff = tariff_for_month(reading_at)
    vat = vat_for_month(reading_at)
    assert tariff is not None and vat is not None
    purpose = normalize_purpose(usage_purpose)
    if purpose == "SINH_HOAT":
        energy_charge = _residential_charge(consumption_kwh, tariff)
        tariff_label = "Sinh hoạt lũy tiến 6 bậc"
        estimated = False
    else:
        flat = tariff.flat_tariff(purpose)
        assert flat is not None
        tariff_label, unit_price = flat
        energy_charge = consumption_kwh * Decimal(unit_price)
        estimated = True

    rounded_energy = _round_money(energy_charge)
    vat_amount = _round_money(Decimal(rounded_energy) * vat.rate)
    return ElectricityBill(
        energy_charge_before_vat=rounded_energy,
        vat_amount=vat_amount,
        total_amount=rounded_energy + vat_amount,
        vat_rate=vat.rate,
        tariff_label=tariff_label,
        estimated=estimated,
        tariff_version=tariff.code,
        tariff_source_url=tariff.source_url,
        vat_policy=vat.code,
        vat_source_url=vat.source_url,
    )
