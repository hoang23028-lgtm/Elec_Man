from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Integer, String, case, cast, distinct, extract, func, select
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.customer import Customer
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.models.processing_job import JobStatus, ProcessingJob
from app.schemas.dashboard import (
    BillingDashboard,
    BillingRecord,
    BillingSummary,
    BillingTrendPoint,
)
from app.services.electricity_tariff_service import calculate_electricity_bill, vat_rate_for


def statistics(db: Session) -> dict:
    """Return all dashboard counters with one database round trip."""
    statement = select(
        select(func.count(Batch.id)).scalar_subquery().label("batches"),
        select(func.count(ImageRecord.id)).scalar_subquery().label("images"),
        *[
            func.count(ProcessingJob.id)
            .filter(ProcessingJob.status == job_status)
            .label(job_status.value.lower())
            for job_status in JobStatus
        ],
    ).select_from(ProcessingJob)
    row = db.execute(statement).one()
    return {
        "batches": int(row.batches),
        "images": int(row.images),
        "jobs": {
            job_status: int(getattr(row, job_status.value.lower())) for job_status in JobStatus
        },
    }


def _billing_source():
    reading_at = func.coalesce(MeterReading.reviewed_at, MeterReading.created_at)
    ordering = (reading_at.asc(), MeterReading.id.asc())
    return (
        select(
            MeterReading.id.label("reading_id"),
            MeterReading.final_customer_id.label("customer_id"),
            MeterReading.final_meter_reading.label("current_reading"),
            MeterReading.reading_value.label("current_value"),
            Customer.initial_reading.label("initial_value"),
            Customer.usage_purpose.label("usage_purpose"),
            reading_at.label("reading_at"),
            func.lag(MeterReading.final_meter_reading)
            .over(partition_by=MeterReading.final_customer_id, order_by=ordering)
            .label("previous_reading"),
            func.lag(MeterReading.reading_value)
            .over(partition_by=MeterReading.final_customer_id, order_by=ordering)
            .label("previous_value"),
        )
        .where(
            MeterReading.review_status == "CONFIRMED",
            MeterReading.final_customer_id.is_not(None),
            MeterReading.final_meter_reading.is_not(None),
            MeterReading.reading_value.is_not(None),
        )
        .outerjoin(Customer, Customer.id == MeterReading.matched_customer_id)
        .cte("confirmed_meter_history")
    )


def _consumption(source):
    previous_value = func.coalesce(source.c.previous_value, source.c.initial_value)
    return case(
        (
            previous_value.is_not(None) & (source.c.current_value >= previous_value),
            source.c.current_value - previous_value,
        ),
        else_=None,
    )


def _apply_billing_filters(statement, source, customer_id, month, year):
    if customer_id and customer_id.strip():
        statement = statement.where(source.c.customer_id.ilike(f"%{customer_id.strip()}%"))
    if month is not None:
        statement = statement.where(extract("month", source.c.reading_at) == month)
    if year is not None:
        statement = statement.where(extract("year", source.c.reading_at) == year)
    return statement


def billing_dashboard(
    db: Session,
    customer_id: str | None,
    month: int | None,
    year: int | None,
    offset: int,
    limit: int,
) -> BillingDashboard:
    source = _billing_source()
    consumption = _consumption(source).label("consumption")
    vat_reference = date(year, month or 1, 1) if year else datetime.now(UTC)

    aggregate_statement = _apply_billing_filters(
        select(
            func.count(source.c.reading_id).label("total_records"),
            func.count(distinct(source.c.customer_id)).label("total_customers"),
            func.coalesce(func.sum(consumption), 0).label("total_consumption"),
        ).select_from(source),
        source,
        customer_id,
        month,
        year,
    )
    aggregate = db.execute(aggregate_statement).one()
    total_consumption = Decimal(aggregate.total_consumption)

    bill_inputs = db.execute(
        _apply_billing_filters(
            select(
                source.c.reading_id,
                source.c.reading_at,
                source.c.usage_purpose,
                consumption,
            ).select_from(source),
            source,
            customer_id,
            month,
            year,
        )
    ).all()
    calculated_bills = {
        row.reading_id: calculate_electricity_bill(
            Decimal(row.consumption), row.usage_purpose or "", row.reading_at
        )
        for row in bill_inputs
        if row.consumption is not None
    }
    calculated_bills = {key: value for key, value in calculated_bills.items() if value}
    billed_records = len(calculated_bills)
    billable_consumption = sum(
        (Decimal(row.consumption) for row in bill_inputs if row.reading_id in calculated_bills),
        Decimal("0"),
    )
    total_before_vat = sum(bill.energy_charge_before_vat for bill in calculated_bills.values())
    total_vat = sum(bill.vat_amount for bill in calculated_bills.values())

    records_statement = _apply_billing_filters(
        select(
            source.c.reading_id,
            source.c.customer_id,
            source.c.current_reading,
            source.c.reading_at,
            func.coalesce(source.c.previous_reading, cast(source.c.initial_value, String)).label(
                "previous_reading"
            ),
            source.c.usage_purpose,
            consumption,
        ).select_from(source),
        source,
        customer_id,
        month,
        year,
    )
    records = db.execute(
        records_statement.order_by(source.c.reading_at.desc(), source.c.reading_id.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    trend_groups = defaultdict(
        lambda: {"record_count": 0, "consumption": Decimal("0"), "before_vat": 0, "vat": 0}
    )
    for row in bill_inputs:
        key = (row.reading_at.year, row.reading_at.month)
        group = trend_groups[key]
        group["record_count"] += 1
        if row.consumption is not None:
            group["consumption"] += Decimal(row.consumption)
        bill = calculated_bills.get(row.reading_id)
        if bill:
            group["before_vat"] += bill.energy_charge_before_vat
            group["vat"] += bill.vat_amount
    available_years = list(
        db.scalars(
            select(cast(extract("year", source.c.reading_at), Integer))
            .distinct()
            .order_by(cast(extract("year", source.c.reading_at), Integer).desc())
        )
    )

    return BillingDashboard(
        summary=BillingSummary(
            total_customers=int(aggregate.total_customers),
            total_records=int(aggregate.total_records),
            billed_records=billed_records,
            total_consumption_kwh=float(total_consumption),
            average_consumption_kwh=(
                float(billable_consumption / billed_records) if billed_records else None
            ),
            energy_charge_before_vat_vnd=total_before_vat,
            vat_amount_vnd=total_vat,
            estimated_amount_vnd=total_before_vat + total_vat,
        ),
        records=[
            BillingRecord(
                reading_id=row.reading_id,
                customer_id=row.customer_id,
                reading_at=row.reading_at,
                month=row.reading_at.month,
                year=row.reading_at.year,
                previous_reading=row.previous_reading,
                current_reading=row.current_reading,
                consumption_kwh=float(row.consumption) if row.consumption is not None else None,
                energy_charge_before_vat_vnd=(
                    calculated_bills[row.reading_id].energy_charge_before_vat
                    if row.reading_id in calculated_bills
                    else None
                ),
                vat_amount_vnd=(
                    calculated_bills[row.reading_id].vat_amount
                    if row.reading_id in calculated_bills
                    else None
                ),
                estimated_amount_vnd=(
                    calculated_bills[row.reading_id].total_amount
                    if row.reading_id in calculated_bills
                    else None
                ),
                tariff_label=(
                    calculated_bills[row.reading_id].tariff_label
                    if row.reading_id in calculated_bills
                    else None
                ),
                tariff_estimated=(
                    calculated_bills[row.reading_id].estimated
                    if row.reading_id in calculated_bills
                    else False
                ),
            )
            for row in records
        ],
        trend=[
            BillingTrendPoint(
                month=key[1],
                year=key[0],
                record_count=group["record_count"],
                consumption_kwh=float(group["consumption"]),
                energy_charge_before_vat_vnd=group["before_vat"],
                vat_amount_vnd=group["vat"],
                estimated_amount_vnd=group["before_vat"] + group["vat"],
            )
            for key, group in sorted(trend_groups.items())
        ],
        available_years=available_years,
        vat_rate_percent=int(vat_rate_for(vat_reference) * 100),
        total=int(aggregate.total_records),
        offset=offset,
        limit=limit,
    )
