def validate(customer_id: str | None, meter_reading: str | None) -> dict:
    errors: list[str] = []
    if not customer_id:
        errors.append("missing_customer_id")
    if not meter_reading:
        errors.append("missing_meter_reading")
    return {"valid": not errors, "errors": errors}
