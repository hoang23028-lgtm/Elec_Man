from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from app.models.ai_result import AiResult
from app.models.meter_reading import MeterReading
from app.schemas.evaluation import EvaluationSummary


def _digit_counts(predicted: str | None, expected: str | None) -> tuple[int, int]:
    left = "".join(character for character in (predicted or "") if character.isdigit())
    right = "".join(character for character in (expected or "") if character.isdigit())
    total = max(len(left), len(right))
    return sum(a == b for a, b in zip(left, right, strict=False)), total


def evaluation_summary(db: Session, model_version: str | None) -> EvaluationSummary:
    filter_clause = AiResult.model_version == model_version if model_version else true()
    total_predictions, review_count, auto_pass_count = db.execute(
        select(
            func.count(AiResult.id),
            func.count(AiResult.id).filter(AiResult.status == "REVIEW"),
            func.count(AiResult.id).filter(AiResult.status == "OK"),
        ).where(filter_clause)
    ).one()
    confirmed = db.execute(
        select(
            AiResult.customer_id_ai,
            AiResult.meter_reading_ai,
            MeterReading.final_customer_id,
            MeterReading.final_meter_reading,
        )
        .join(MeterReading, MeterReading.ai_result_id == AiResult.id)
        .where(MeterReading.review_status == "CONFIRMED", filter_clause)
    ).all()
    customer_matches = sum(
        predicted_customer == final_customer
        for predicted_customer, _, final_customer, _ in confirmed
    )
    meter_matches = sum(
        predicted_meter == final_meter for _, predicted_meter, _, final_meter in confirmed
    )
    digit_correct = 0
    digit_total = 0
    for _, predicted_meter, _, final_meter in confirmed:
        correct, total = _digit_counts(predicted_meter, final_meter)
        digit_correct += correct
        digit_total += total
    sample_count = len(confirmed)
    return EvaluationSummary(
        model_version=model_version,
        total_predictions=total_predictions,
        confirmed_samples=sample_count,
        customer_exact_accuracy=round(customer_matches / sample_count, 4) if sample_count else None,
        meter_exact_accuracy=round(meter_matches / sample_count, 4) if sample_count else None,
        meter_digit_accuracy=round(digit_correct / digit_total, 4) if digit_total else None,
        review_rate=round(review_count / total_predictions, 4) if total_predictions else 0.0,
        auto_pass_rate=round(auto_pass_count / total_predictions, 4) if total_predictions else 0.0,
        false_auto_pass_rate=None,
    )
