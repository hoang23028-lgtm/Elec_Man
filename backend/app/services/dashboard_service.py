from decimal import Decimal

from sqlalchemy import Integer, String, case, cast, distinct, extract, func, select
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.confirmed_monthly_reading import ConfirmedMonthlyReading
from app.models.image import ImageRecord
from app.models.processing_job import JobStatus, ProcessingJob
from app.schemas.dashboard import (
    BillingDashboard,
    BillingRecord,
    BillingSummary,
    BillingTrendPoint,
)
from app.services.billing_query import bill_amounts, vat_rate_expression
from app.services.electricity_billing_policy import (
    billing_unavailable_reason,
    tariff_for_month,
    vat_for_month,
)
from app.services.electricity_tariff_service import calculate_electricity_bill


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
    reading_at = ConfirmedMonthlyReading.confirmed_at
    ordering = (ConfirmedMonthlyReading.reading_month.asc(), ConfirmedMonthlyReading.id.asc())
    return select(
        ConfirmedMonthlyReading.id.label("reading_id"),
        ConfirmedMonthlyReading.customer_code.label("customer_id"),
        cast(ConfirmedMonthlyReading.meter_reading, String).label("current_reading"),
        ConfirmedMonthlyReading.meter_reading.label("current_value"),
        ConfirmedMonthlyReading.initial_reading_snapshot.label("initial_value"),
        ConfirmedMonthlyReading.usage_purpose_snapshot.label("usage_purpose"),
        reading_at.label("reading_at"),
        ConfirmedMonthlyReading.reading_month.label("reading_month"),
        func.lag(cast(ConfirmedMonthlyReading.meter_reading, String))
        .over(partition_by=ConfirmedMonthlyReading.customer_id, order_by=ordering)
        .label("previous_reading"),
        func.lag(ConfirmedMonthlyReading.meter_reading)
        .over(partition_by=ConfirmedMonthlyReading.customer_id, order_by=ordering)
        .label("previous_value"),
        func.lag(ConfirmedMonthlyReading.reading_month)
        .over(partition_by=ConfirmedMonthlyReading.customer_id, order_by=ordering)
        .label("previous_month"),
    ).cte("confirmed_meter_history")


def _consumption(source):
    previous_value = func.coalesce(source.c.previous_value, source.c.initial_value)
    month_distance = (
        (extract("year", source.c.reading_month) - extract("year", source.c.previous_month)) * 12
        + extract("month", source.c.reading_month)
        - extract("month", source.c.previous_month)
    )
    return case(
        (
            previous_value.is_not(None)
            & (source.c.current_value >= previous_value)
            & (source.c.previous_month.is_(None) | (month_distance == 1)),
            source.c.current_value - previous_value,
        ),
        else_=None,
    )


def _apply_billing_filters(statement, source, customer_id, month, year):
    if customer_id and customer_id.strip():
        statement = statement.where(source.c.customer_id.ilike(f"%{customer_id.strip()}%"))
    if month is not None:
        statement = statement.where(extract("month", source.c.reading_month) == month)
    if year is not None:
        statement = statement.where(extract("year", source.c.reading_month) == year)
    return statement


def _billing_record(row) -> BillingRecord:
    consumption = Decimal(row.consumption) if row.consumption is not None else None
    purpose = row.usage_purpose or ""
    bill = (
        calculate_electricity_bill(consumption, purpose, row.reading_month)
        if consumption is not None
        else None
    )
    tariff = tariff_for_month(row.reading_month)
    vat = vat_for_month(row.reading_month)
    return BillingRecord(
        reading_id=row.reading_id,
        customer_id=row.customer_id,
        reading_at=row.reading_at,
        month=row.reading_month.month,
        year=row.reading_month.year,
        previous_reading=row.previous_reading,
        current_reading=row.current_reading,
        consumption_kwh=float(consumption) if consumption is not None else None,
        energy_charge_before_vat_vnd=bill.energy_charge_before_vat if bill else None,
        vat_amount_vnd=bill.vat_amount if bill else None,
        estimated_amount_vnd=bill.total_amount if bill else None,
        tariff_label=bill.tariff_label if bill else None,
        tariff_estimated=bill.estimated if bill else False,
        tariff_version=tariff.code if tariff else None,
        tariff_source_url=tariff.source_url if tariff else None,
        vat_rate_percent=int(vat.rate * 100) if vat else None,
        vat_policy=vat.code if vat else None,
        vat_source_url=vat.source_url if vat else None,
        billing_note=billing_unavailable_reason(consumption, purpose, row.reading_month),
    )


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
    energy, vat = bill_amounts(consumption, source.c.usage_purpose, source.c.reading_month)
    billable_vat_percent = case(
        (energy.is_not(None), vat_rate_expression(source.c.reading_month) * 100), else_=None
    )

    aggregate_statement = _apply_billing_filters(
        select(
            func.count(source.c.reading_id).label("total_records"),
            func.count(distinct(source.c.customer_id)).label("total_customers"),
            func.coalesce(func.sum(consumption), 0).label("total_consumption"),
            func.count(energy).label("billed_records"),
            func.coalesce(func.sum(case((energy.is_not(None), consumption), else_=0)), 0).label(
                "billable_consumption"
            ),
            func.coalesce(func.sum(energy), 0).label("before_vat"),
            func.coalesce(func.sum(vat), 0).label("vat"),
            func.min(billable_vat_percent).label("min_vat_percent"),
            func.max(billable_vat_percent).label("max_vat_percent"),
        ).select_from(source),
        source,
        customer_id,
        month,
        year,
    )
    aggregate = db.execute(aggregate_statement).one()
    total_consumption = Decimal(aggregate.total_consumption)

    trend_rows = db.execute(
        _apply_billing_filters(
            select(
                source.c.reading_month,
                func.count().label("record_count"),
                func.coalesce(func.sum(consumption), 0).label("consumption"),
                func.coalesce(func.sum(energy), 0).label("before_vat"),
                func.coalesce(func.sum(vat), 0).label("vat"),
            )
            .select_from(source)
            .group_by(source.c.reading_month)
            .order_by(source.c.reading_month),
            source,
            customer_id,
            month,
            year,
        )
    ).all()
    billed_records = int(aggregate.billed_records)
    billable_consumption = Decimal(aggregate.billable_consumption)
    total_before_vat = int(aggregate.before_vat)
    total_vat = int(aggregate.vat)

    records_statement = _apply_billing_filters(
        select(
            source.c.reading_id,
            source.c.customer_id,
            source.c.current_reading,
            source.c.reading_at,
            source.c.reading_month,
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

    available_years = list(
        db.scalars(
            select(cast(extract("year", source.c.reading_month), Integer))
            .distinct()
            .order_by(cast(extract("year", source.c.reading_month), Integer).desc())
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
        records=[_billing_record(row) for row in records],
        trend=[
            BillingTrendPoint(
                month=row.reading_month.month,
                year=row.reading_month.year,
                record_count=row.record_count,
                consumption_kwh=float(row.consumption),
                energy_charge_before_vat_vnd=int(row.before_vat),
                vat_amount_vnd=int(row.vat),
                estimated_amount_vnd=int(row.before_vat + row.vat),
            )
            for row in trend_rows
        ],
        available_years=available_years,
        vat_rate_percent=(
            int(aggregate.min_vat_percent)
            if aggregate.min_vat_percent is not None
            and aggregate.min_vat_percent == aggregate.max_vat_percent
            else None
        ),
        total=int(aggregate.total_records),
        offset=offset,
        limit=limit,
    )
