def calculate(
    customer_confidence: float,
    meter_confidence: float,
    detection_confidence: float,
    quality_score: float,
    valid: bool,
) -> float:
    if not valid:
        return 0.0
    return round(
        min(customer_confidence, meter_confidence, detection_confidence) * 0.75
        + quality_score * 0.25,
        4,
    )
