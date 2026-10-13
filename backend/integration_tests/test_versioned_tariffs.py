"""Check the production SQL dialect, not just SQLite's date/numeric behavior."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import literal, select

from app.core.database import SessionLocal
from app.services.billing_query import bill_amounts
from app.services.electricity_tariff_service import calculate_electricity_bill


@pytest.mark.parametrize(
    "month,purpose,energy,vat",
    [
        (date(2025, 4, 1), "SINH_HOAT", 192450, 15396),
        (date(2025, 4, 1), "HO_SAN_XUAT", 189600, 15168),
        (date(2025, 4, 1), "VIETTEL", 300700, 24056),
        (date(2025, 4, 1), "TRUONG_HOC_Y_TE", 197700, 15816),
        (date(2025, 4, 1), "UB_HANH_CHINH", 212400, 16992),
        (date(2025, 5, 1), "SINH_HOAT", None, None),
        (date(2024, 12, 1), "SINH_HOAT", None, None),
        (date(2025, 6, 1), "SINH_HOAT", 201700, 16136),
        (date(2025, 7, 1), "SINH_HOAT", 201700, 16136),
        (date(2026, 12, 1), "SINH_HOAT", 201700, 16136),
        (date(2027, 1, 1), "SINH_HOAT", 201700, 20170),
        (date(2026, 1, 1), "UNKNOWN", None, None),
    ],
)
def test_verified_versions_match_postgres_numeric_totals(month, purpose, energy, vat):
    expressions = bill_amounts(literal(Decimal(100)), literal(purpose), literal(month))
    with SessionLocal() as db:
        assert tuple(db.execute(select(*expressions)).one()) == (energy, vat)
    detail = calculate_electricity_bill(Decimal(100), purpose, month)
    actual = (detail.energy_charge_before_vat, detail.vat_amount) if detail else (None, None)
    assert actual == (energy, vat)
