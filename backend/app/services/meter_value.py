import re
from decimal import Decimal, InvalidOperation

METER_VALUE_PATTERN = re.compile(r"^\d{1,11}(?:[.,]\d{1,3})?$")


def parse_meter_value(value: str | None) -> Decimal | None:
    if value is None:
        return None
    normalized = value.strip().replace(",", ".")
    if not METER_VALUE_PATTERN.fullmatch(normalized):
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None
