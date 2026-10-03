from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.ai_result_service import store_immutable_ai_result


def test_reading_only_preserves_customer_and_automatic_region():
    existing = SimpleNamespace(
        customer_id_ai="PN2.001",
        customer_confidence=0.8,
        raw_result_json={"regions": {"reading": [10, 20, 30, 40]}},
    )
    db = MagicMock()
    db.scalar.return_value = existing
    result = dict(
        reading_only=True,
        customer_id_ai=None,
        customer_confidence=0,
        model_version="test",
        meter_reading_ai="01234",
        meter_confidence=0.9,
        detection_confidence=1,
        image_quality_score=0.8,
        final_confidence=0.9,
        status="REVIEW",
        processing_time_ms=100,
        regions={"human_reading": [[1, 2], [3, 2], [3, 4], [1, 4]]},
    )
    stored = store_immutable_ai_result(db, "image", result, replace_existing=True)
    assert stored.customer_id_ai == result["customer_id_ai"] == "PN2.001"
    assert stored.customer_confidence == 0.8
    assert stored.raw_result_json["regions"]["reading"] == [10, 20, 30, 40]
    assert "human_reading" in stored.raw_result_json["regions"]
