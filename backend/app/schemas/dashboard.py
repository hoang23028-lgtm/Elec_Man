from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BillingSummary(BaseModel):
    total_customers: int
    total_records: int
    billed_records: int
    total_consumption_kwh: float
    average_consumption_kwh: float | None
    energy_charge_before_vat_vnd: int
    vat_amount_vnd: int
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
    energy_charge_before_vat_vnd: int | None
    vat_amount_vnd: int | None
    estimated_amount_vnd: int | None
    tariff_label: str | None
    tariff_estimated: bool


class BillingTrendPoint(BaseModel):
    month: int
    year: int
    record_count: int
    consumption_kwh: float
    energy_charge_before_vat_vnd: int
    vat_amount_vnd: int
    estimated_amount_vnd: int


class BillingDashboard(BaseModel):
    summary: BillingSummary
    records: list[BillingRecord]
    trend: list[BillingTrendPoint]
    available_years: list[int]
    vat_rate_percent: int
    total: int
    offset: int
    limit: int
