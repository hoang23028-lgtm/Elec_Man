import json
import re
from collections.abc import Iterable

from fastapi import HTTPException, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerImportResponse,
    CustomerImportRow,
    CustomerRow,
    CustomerSummary,
)

CUSTOMER_ROWS_ADAPTER = TypeAdapter(list[CustomerImportRow])
MAX_CUSTOMER_ROWS = 10_000


def normalize_customer_code(value: str | None) -> str:
    """Create a punctuation-insensitive key without changing the stored customer code."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").strip().upper())


def parse_customer_json(content: bytes) -> list[CustomerImportRow]:
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Tệp phải là JSON UTF-8 hợp lệ.") from exc
    try:
        rows = CUSTOMER_ROWS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        first = exc.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first["loc"])
        raise ValueError(
            f"Dữ liệu khách hàng không hợp lệ tại {location}: {first['msg']}."
        ) from exc
    if not rows:
        raise ValueError("Danh sách khách hàng không được để trống.")
    if len(rows) > MAX_CUSTOMER_ROWS:
        raise ValueError(f"Mỗi lần chỉ được nhập tối đa {MAX_CUSTOMER_ROWS:,} khách hàng.")
    return rows


def _chunks(values: list[str], size: int = 500) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _customers_by_lookup(db: Session, keys: set[str]) -> dict[str, Customer]:
    result: dict[str, Customer] = {}
    for chunk in _chunks(sorted(keys)):
        for customer in db.scalars(select(Customer).where(Customer.lookup_key.in_(chunk))):
            result[customer.lookup_key] = customer
    return result


def find_customer(db: Session, customer_code: str | None) -> Customer | None:
    lookup_key = normalize_customer_code(customer_code)
    if not lookup_key:
        return None
    return db.scalar(select(Customer).where(Customer.lookup_key == lookup_key))


def apply_customer_match(reading: MeterReading, customer: Customer | None) -> None:
    reading.matched_customer_id = customer.id if customer else None
    reading.customer_match_status = (
        "MATCHED" if customer else "NOT_FOUND" if reading.final_customer_id else "NOT_CHECKED"
    )
    if customer is not None:
        reading.final_customer_id = customer.customer_code


def reconcile_confirmed_readings(db: Session) -> int:
    readings = list(
        db.scalars(
            select(MeterReading).where(
                MeterReading.review_status == "CONFIRMED",
                MeterReading.final_customer_id.is_not(None),
            )
        )
    )
    keys = {normalize_customer_code(row.final_customer_id) for row in readings}
    customers = _customers_by_lookup(db, {key for key in keys if key})
    changed = 0
    for reading in readings:
        customer = customers.get(normalize_customer_code(reading.final_customer_id))
        previous = (reading.matched_customer_id, reading.customer_match_status)
        apply_customer_match(reading, customer)
        if previous != (reading.matched_customer_id, reading.customer_match_status):
            changed += 1
    return changed


def import_customers(db: Session, rows: list[CustomerImportRow]) -> CustomerImportResponse:
    lookup_keys = [normalize_customer_code(row.customer_code) for row in rows]
    serials = [row.meter_serial.upper() for row in rows]
    if any(not key for key in lookup_keys):
        raise ValueError("Mã khách hàng phải có ít nhất một chữ cái hoặc chữ số.")
    if len(set(lookup_keys)) != len(lookup_keys):
        raise ValueError("Tệp chứa mã khách hàng bị trùng sau khi chuẩn hóa.")
    if len(set(serials)) != len(serials):
        raise ValueError("Tệp chứa số serial công tơ bị trùng.")

    existing_by_key = _customers_by_lookup(db, set(lookup_keys))
    existing_by_serial: dict[str, Customer] = {}
    for chunk in _chunks(sorted(set(serials))):
        for customer in db.scalars(
            select(Customer).where(func.upper(Customer.meter_serial).in_(chunk))
        ):
            existing_by_serial[customer.meter_serial.upper()] = customer

    created = 0
    updated = 0
    for row, lookup_key, serial_key in zip(rows, lookup_keys, serials, strict=True):
        customer = existing_by_key.get(lookup_key)
        serial_owner = existing_by_serial.get(serial_key)
        if serial_owner is not None and serial_owner is not customer:
            raise ValueError(f"Số serial {row.meter_serial} đã thuộc mã khách hàng khác.")
        if customer is None:
            customer = Customer(lookup_key=lookup_key)
            db.add(customer)
            existing_by_key[lookup_key] = customer
            created += 1
        else:
            updated += 1
        customer.customer_code = row.customer_code
        customer.full_name = row.full_name
        customer.address = row.address
        customer.electricity_route = row.electricity_route
        customer.meter_serial = row.meter_serial
        customer.initial_reading = row.initial_reading
        customer.usage_purpose = row.usage_purpose

    db.flush()
    reconciled = reconcile_confirmed_readings(db)
    return CustomerImportResponse(
        total=len(rows), created=created, updated=updated, reconciled_readings=reconciled
    )


def customer_summary(db: Session) -> CustomerSummary:
    total = int(db.scalar(select(func.count(Customer.id))) or 0)
    matched, unmatched = db.execute(
        select(
            func.count(MeterReading.id).filter(MeterReading.customer_match_status == "MATCHED"),
            func.count(MeterReading.id).filter(MeterReading.customer_match_status == "NOT_FOUND"),
        ).where(MeterReading.review_status == "CONFIRMED")
    ).one()
    return CustomerSummary(
        total=total, matched_readings=int(matched), unmatched_readings=int(unmatched)
    )


def list_usage_purposes(db: Session) -> list[str]:
    """Return only usage purposes currently present in customer data."""
    stored_values = db.scalars(
        select(Customer.usage_purpose)
        .where(Customer.usage_purpose.is_not(None), Customer.usage_purpose != "")
        .distinct()
    ).all()
    return sorted({value.strip() for value in stored_values if value.strip()})


def list_customers(
    db: Session,
    offset: int,
    limit: int,
    search: str | None = None,
) -> tuple[list[CustomerRow], int]:
    statement = select(Customer)
    count_statement = select(func.count(Customer.id))
    if search:
        pattern = f"%{search.strip()}%"
        condition = or_(
            Customer.customer_code.ilike(pattern),
            Customer.full_name.ilike(pattern),
            Customer.meter_serial.ilike(pattern),
            Customer.electricity_route.ilike(pattern),
        )
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    total = int(db.scalar(count_statement) or 0)
    rows = db.scalars(
        statement.order_by(Customer.customer_code.asc()).offset(offset).limit(limit)
    ).all()
    return [CustomerRow.model_validate(row) for row in rows], total


def create_customer(
    db: Session,
    payload: CustomerCreate,
    actor: User,
    ip_address: str | None,
) -> CustomerRow:
    lookup_key = normalize_customer_code(payload.customer_code)
    if not lookup_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Mã khách hàng phải có ít nhất một chữ cái hoặc chữ số.",
        )
    if db.scalar(select(Customer.id).where(Customer.lookup_key == lookup_key)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mã khách hàng đã tồn tại.",
        )
    if (
        db.scalar(
            select(Customer.id).where(
                func.upper(Customer.meter_serial) == payload.meter_serial.upper()
            )
        )
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Số serial công tơ đã thuộc khách hàng khác.",
        )

    customer = Customer(
        customer_code=payload.customer_code,
        lookup_key=lookup_key,
        full_name=payload.full_name,
        address=payload.address,
        electricity_route=payload.electricity_route,
        meter_serial=payload.meter_serial,
        initial_reading=payload.initial_reading,
        usage_purpose=payload.usage_purpose,
    )
    db.add(customer)
    try:
        db.flush()
        reconciled = reconcile_confirmed_readings(db)
        db.add(
            AuditLog(
                user_id=actor.id,
                action="CREATE_CUSTOMER",
                target_type="customer",
                target_id=str(customer.id),
                details_json={
                    "customer_code": customer.customer_code,
                    "full_name": customer.full_name,
                    "address": customer.address,
                    "electricity_route": customer.electricity_route,
                    "meter_serial": customer.meter_serial,
                    "initial_reading": customer.initial_reading,
                    "usage_purpose": customer.usage_purpose,
                    "reconciled_readings": reconciled,
                },
                ip_address=ip_address,
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mã khách hàng hoặc số serial công tơ đã tồn tại.",
        ) from exc
    db.refresh(customer)
    return CustomerRow.model_validate(customer)
