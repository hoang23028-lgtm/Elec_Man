from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_result import AiResult


def store_immutable_ai_result(
    db: Session, image_id: object, result: dict, *, replace_existing: bool = False
) -> AiResult:
    existing = db.scalar(select(AiResult).where(AiResult.image_id == image_id))
    if existing is not None and replace_existing:
        existing.model_version = result["model_version"]
        existing.customer_id_ai = result["customer_id_ai"]
        existing.meter_reading_ai = result["meter_reading_ai"]
        existing.customer_confidence = result["customer_confidence"]
        existing.meter_confidence = result["meter_confidence"]
        existing.detection_confidence = result["detection_confidence"]
        existing.image_quality_score = result["image_quality_score"]
        existing.final_confidence = result["final_confidence"]
        existing.status = result["status"]
        existing.processing_time_ms = result["processing_time_ms"]
        existing.raw_result_json = result
        db.flush()
        return existing
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
