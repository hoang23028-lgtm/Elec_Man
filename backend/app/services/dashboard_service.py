from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Integer, case, cast, distinct, extract, func, select
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.models.processing_job import JobStatus, ProcessingJob
from app.models.system_setting import SystemSetting
from app.schemas.dashboard import (
    BillingDashboard,
    BillingRecord,
    BillingSummary,
    BillingTrendPoint,
)

DEFAULT_ELECTRICITY_UNIT_PRICE_VND = 2500


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


def _unit_price(db: Session) -> int:
    setting = db.get(SystemSetting, "electricity_unit_price_vnd")
    try:
        value = int(setting.value_json) if setting else DEFAULT_ELECTRICITY_UNIT_PRICE_VND
    except (TypeError, ValueError):
        return DEFAULT_ELECTRICITY_UNIT_PRICE_VND
    return value if value > 0 else DEFAULT_ELECTRICITY_UNIT_PRICE_VND


def _amount(consumption: Decimal | None, unit_price: int) -> int | None:
    if consumption is None:
        return None
    return int((consumption * unit_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _billing_source():
    reading_at = func.coalesce(MeterReading.reviewed_at, MeterReading.created_at)
    ordering = (reading_at.asc(), MeterReading.id.asc())
    return (
        select(
            MeterReading.id.label("reading_id"),
            MeterReading.final_customer_id.label("customer_id"),
            MeterReading.final_meter_reading.label("current_reading"),
            MeterReading.reading_value.label("current_value"),
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
        .cte("confirmed_meter_history")
    )


def _consumption(source):
    return case(
        (
            source.c.previous_value.is_not(None)
            & (source.c.current_value >= source.c.previous_value),
            source.c.current_value - source.c.previous_value,
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
    unit_price = _unit_price(db)

    aggregate_statement = _apply_billing_filters(
        select(
            func.count(source.c.reading_id).label("total_records"),
            func.count(distinct(source.c.customer_id)).label("total_customers"),
            func.count(consumption).label("billed_records"),
            func.coalesce(func.sum(consumption), 0).label("total_consumption"),
        ).select_from(source),
        source,
        customer_id,
        month,
        year,
    )
    aggregate = db.execute(aggregate_statement).one()
    total_consumption = Decimal(aggregate.total_consumption)
    billed_records = int(aggregate.billed_records)

    records_statement = _apply_billing_filters(
        select(
            source.c.reading_id,
            source.c.customer_id,
            source.c.current_reading,
            source.c.reading_at,
            source.c.previous_reading,
            consumption,
        ).select_from(source),
        source,
        customer_id,
        month,
        year,
    )
    records = db.execute(
        records_statement
        .order_by(source.c.reading_at.desc(), source.c.reading_id.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    year_part = cast(extract("year", source.c.reading_at), Integer).label("year")
    month_part = cast(extract("month", source.c.reading_at), Integer).label("month")
    trend_statement = _apply_billing_filters(
        select(
            year_part,
            month_part,
            func.count(source.c.reading_id).label("record_count"),
            func.coalesce(func.sum(consumption), 0).label("consumption"),
        )
        .select_from(source)
        .group_by(year_part, month_part)
        .order_by(year_part, month_part),
        source,
        customer_id,
        month,
        year,
    )
    trends = db.execute(trend_statement).all()
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
                float(total_consumption / billed_records) if billed_records else None
            ),
            estimated_amount_vnd=_amount(total_consumption, unit_price) or 0,
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
                estimated_amount_vnd=_amount(row.consumption, unit_price),
            )
            for row in records
        ],
        trend=[
            BillingTrendPoint(
                month=row.month,
                year=row.year,
                record_count=row.record_count,
                consumption_kwh=float(row.consumption),
                estimated_amount_vnd=_amount(Decimal(row.consumption), unit_price) or 0,
            )
            for row in trends
        ],
        available_years=available_years,
        unit_price_vnd=unit_price,
        total=int(aggregate.total_records),
        offset=offset,
        limit=limit,
    )
