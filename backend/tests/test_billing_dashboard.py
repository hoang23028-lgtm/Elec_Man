from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.models.customer import Customer
from app.services.dashboard_service import billing_dashboard


def test_history_filters_pagination_gaps_and_customer_edits():
    engine = create_engine("sqlite://")
    Customer.__table__.create(engine)
    ConfirmedMonthlyReading.__table__.create(engine)
    customer_id = uuid4()
    with Session(engine) as db:
        customer = Customer(
            id=customer_id,
            customer_code="PN2.001",
            lookup_key="pn2001",
            full_name="Test",
            address="Test",
            electricity_route="Test",
            meter_serial="Test",
            initial_reading=0,
            usage_purpose="SINH_HOAT",
        )
        db.add(customer)
        for month, reading in [
            (date(2025, 12, 1), 100),
            (date(2026, 1, 1), 200),
            (date(2026, 3, 1), 400),
        ]:
            db.add(
                ConfirmedMonthlyReading(
                    customer_id=customer_id,
                    source_image_id=uuid4(),
                    customer_code="PN2.001",
                    reading_month=month,
                    meter_reading=reading,
                    initial_reading_snapshot=0,
                    usage_purpose_snapshot="SINH_HOAT",
                    original_filename="test.jpg",
                    image_mime_type="image/jpeg",
                    image_sha256="a" * 64,
                    image_data=b"test",
                    confirmed_at=datetime(month.year, month.month, 15, tzinfo=UTC),
                )
            )
        db.commit()
        before = billing_dashboard(db, None, None, None, 0, 10)
        assert before.total == 3
        assert before.summary.billed_records == 2
        assert before.summary.total_consumption_kwh == 200
        assert before.records[0].consumption_kwh is None
        assert before.records[0].estimated_amount_vnd is None
        assert before.summary.estimated_amount_vnd == sum(
            row.estimated_amount_vnd or 0 for row in before.records
        )
        customer.initial_reading = 9999
        customer.usage_purpose = "KINH_DOANH"
        db.commit()
        after = billing_dashboard(db, None, None, None, 0, 10)
        assert before == after
        page = billing_dashboard(db, "PN2", None, 2026, 1, 1)
        assert page.total == 2
        assert len(page.records) == 1
        assert page.records[0].month == 1
        assert page.records[0].consumption_kwh == Decimal(100)
        assert page.summary.billed_records == 1
        assert page.available_years == [2026, 2025]
    engine.dispose()


def test_dashboard_versions_notes_and_mixed_vat_match_all_totals():
    engine = create_engine("sqlite://")
    Customer.__table__.create(engine)
    ConfirmedMonthlyReading.__table__.create(engine)
    periods = [
        (date(2024, 9, 1), None),
        (date(2024, 12, 1), None),
        (date(2025, 4, 1), 192450),
        (date(2025, 5, 1), None),
        (date(2025, 6, 1), 201700),
        (date(2025, 7, 1), 201700),
        (date(2026, 12, 1), 201700),
        (date(2027, 1, 1), 201700),
    ]
    with Session(engine) as db:
        for index, (month, _) in enumerate(periods):
            customer_id = uuid4()
            code = f"TARIFF.{index}"
            db.add(
                Customer(
                    id=customer_id,
                    customer_code=code,
                    lookup_key=f"tariff{index}",
                    full_name="Test",
                    address="Test",
                    electricity_route="Test",
                    meter_serial=code,
                    initial_reading=100,
                    usage_purpose="SINH_HOAT",
                )
            )
            db.add(
                ConfirmedMonthlyReading(
                    customer_id=customer_id,
                    source_image_id=uuid4(),
                    customer_code=code,
                    reading_month=month,
                    meter_reading=200,
                    initial_reading_snapshot=100,
                    usage_purpose_snapshot="SINH_HOAT",
                    original_filename="test.jpg",
                    image_mime_type="image/jpeg",
                    image_sha256="a" * 64,
                    image_data=b"test",
                    # Confirmation occurs much later; the calendar period determines the tariff.
                    confirmed_at=datetime(2027, 1, 15, tzinfo=UTC),
                )
            )
        db.commit()
        data = billing_dashboard(db, None, None, None, 0, 20)
        assert data.summary.total_records == 8
        assert data.summary.billed_records == 5
        assert data.summary.total_consumption_kwh == 800
        assert data.vat_rate_percent is None  # An all-years total must not claim only 8%.
        for field in ("energy_charge_before_vat_vnd", "vat_amount_vnd", "estimated_amount_vnd"):
            assert (
                getattr(data.summary, field)
                == sum(getattr(row, field) or 0 for row in data.records)
                == sum(getattr(row, field) for row in data.trend)
            )
        for index, (month, expected_energy) in enumerate(periods):
            row = next(row for row in data.records if row.customer_id == f"TARIFF.{index}")
            assert row.energy_charge_before_vat_vnd == expected_energy
            assert bool(row.billing_note) == (expected_energy is None)
            if expected_energy is not None:
                assert row.tariff_source_url.startswith("https://")
                assert row.vat_source_url.startswith("https://")
                assert row.tariff_version == (
                    "2699/QĐ-BCT" if month < date(2025, 5, 1) else "1279/QĐ-BCT"
                )
        assert (
            "đổi giá giữa kỳ"
            in next(row for row in data.records if row.customer_id == "TARIFF.3").billing_note
        )
        assert billing_dashboard(db, None, 4, 2025, 0, 10).vat_rate_percent == 8
        assert billing_dashboard(db, None, 1, 2027, 0, 10).vat_rate_percent == 10
        assert billing_dashboard(db, None, 5, 2025, 0, 10).vat_rate_percent is None
    engine.dispose()
