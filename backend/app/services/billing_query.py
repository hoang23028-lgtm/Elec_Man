"""Database-side totals use the same effective versions as the detail calculator."""

from decimal import Decimal

from sqlalchemy import case, func

from app.services.electricity_billing_policy import FLAT_PURPOSES, TARIFF_VERSIONS, VAT_VERSIONS


def _month_condition(month, version):
    condition = month >= version.first_full_month
    if version.full_months_until is not None:
        condition &= month < version.full_months_until
    return condition


def vat_rate_expression(reading_month):
    return case(
        *((_month_condition(reading_month, version), version.rate) for version in VAT_VERSIONS),
        else_=None,
    )


def _tariff_charge(consumption, normalized_purpose, version):
    residential = 0
    lower_bound = Decimal(0)
    for allowance, price in version.residential_tiers:
        quantity = case((consumption > lower_bound, consumption - lower_bound), else_=0)
        if allowance is not None:
            quantity = case((quantity > allowance, allowance), else_=quantity)
        residential += quantity * price
        if allowance is not None:
            lower_bound += allowance
    flat_rates = {name: version.flat_tariff(name)[1] for name in FLAT_PURPOSES}
    return case(
        (normalized_purpose == "SINH_HOAT", residential),
        else_=consumption * case(flat_rates, value=normalized_purpose, else_=None),
    )


def bill_amounts(consumption, purpose, reading_month):
    normalized_purpose = func.upper(func.trim(purpose))
    vat_rate = vat_rate_expression(reading_month)
    charge = case(
        (consumption.is_(None) | (consumption < 0) | vat_rate.is_(None), None),
        *(
            (
                _month_condition(reading_month, version),
                _tariff_charge(consumption, normalized_purpose, version),
            )
            for version in TARIFF_VERSIONS
        ),
        else_=None,
    )
    energy = func.round(charge, 0)
    return energy, func.round(energy * vat_rate, 0)
