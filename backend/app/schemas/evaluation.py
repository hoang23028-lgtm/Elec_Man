from pydantic import BaseModel


class EvaluationSummary(BaseModel):
    model_version: str | None
    total_predictions: int
    confirmed_samples: int
    customer_exact_accuracy: float | None
    meter_exact_accuracy: float | None
    meter_digit_accuracy: float | None
    review_rate: float
    auto_pass_rate: float
    false_auto_pass_rate: float | None
