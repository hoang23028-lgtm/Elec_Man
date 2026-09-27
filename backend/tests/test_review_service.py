from types import SimpleNamespace

from app.services.review_service import _normalized_ai_reading_bbox


def test_ai_reading_region_is_normalized_after_preprocessing_resize() -> None:
    image = SimpleNamespace(width=3200, height=1600)
    ai_result = SimpleNamespace(raw_result_json={"regions": {"reading": [400, 200, 800, 300]}})

    bbox = _normalized_ai_reading_bbox(image, ai_result)

    assert bbox is not None
    assert bbox.model_dump() == {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.375}
