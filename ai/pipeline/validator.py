import re


def validate(customer_id: str | None, meter_reading: str | None) -> dict:
    errors: list[str] = []
    if not customer_id:
        errors.append("missing_customer_id")
    if not meter_reading:
        errors.append("missing_meter_reading")
    if customer_id and not re.fullmatch(r"[A-Z][A-Z0-9._-]{2,31}", customer_id):
        errors.append("invalid_customer_id")
    if meter_reading and not re.fullmatch(r"\d{4,8}", meter_reading):
        errors.append("invalid_meter_reading")
    return {"valid": not errors, "errors": errors}
