from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BillingSummary(BaseModel):
    total_customers: int
    total_records: int
    billed_records: int
    total_consumption_kwh: float
    average_consumption_kwh: float | None
    estimated_amount_vnd: int


class BillingRecord(BaseModel):
    reading_id: UUID
    customer_id: str
    reading_at: datetime
    month: int
    year: int
    previous_reading: str | None
    current_reading: str
    consumption_kwh: float | None
    estimated_amount_vnd: int | None


class BillingTrendPoint(BaseModel):
    month: int
    year: int
    record_count: int
    consumption_kwh: float
    estimated_amount_vnd: int


class BillingDashboard(BaseModel):
    summary: BillingSummary
    records: list[BillingRecord]
    trend: list[BillingTrendPoint]
    available_years: list[int]
    unit_price_vnd: int
    total: int
    offset: int
    limit: int
