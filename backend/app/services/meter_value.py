import re
from decimal import Decimal, InvalidOperation

METER_VALUE_PATTERN = re.compile(r"^(\d{1,11})(?:[.,]\d{1,3})?$")


def normalize_meter_reading(value: str | None) -> str | None:
    if value is None:
        return None
    match = METER_VALUE_PATTERN.fullmatch(value.strip())
    return match.group(1) if match else None


def parse_meter_value(value: str | None) -> Decimal | None:
    if value is None:
        return None
    normalized = normalize_meter_reading(value)
    if normalized is None:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None
