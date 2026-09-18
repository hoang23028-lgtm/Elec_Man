from sqlalchemy.orm import Session

from app.models.ai_result import AiResult


def store_immutable_ai_result(db: Session, image_id: object, result: dict) -> AiResult:
    ai_result = AiResult(
        image_id=image_id,
        model_version=result["model_version"],
        customer_id_ai=result["customer_id_ai"],
        meter_reading_ai=result["meter_reading_ai"],
        customer_confidence=result["customer_confidence"],
        meter_confidence=result["meter_confidence"],
        detection_confidence=result["detection_confidence"],
        image_quality_score=result["image_quality_score"],
        final_confidence=result["final_confidence"],
        status=result["status"],
        processing_time_ms=result["processing_time_ms"],
        raw_result_json=result,
    )
    db.add(ai_result)
    db.flush()
    return ai_result
