import pytest
from pydantic import ValidationError

from app.schemas.result import ReadingBoundingBox, ReviewRequest


def test_reading_bbox_accepts_normalized_coordinates() -> None:
    payload = ReviewRequest(
        action="CONFIRM",
        final_customer_id="PN2.001",
        final_meter_reading="63751",
        reading_bbox={"x": 0.2, "y": 0.3, "width": 0.5, "height": 0.1},
    )

    assert payload.reading_bbox == ReadingBoundingBox(x=0.2, y=0.3, width=0.5, height=0.1)


def test_reading_bbox_rejects_region_outside_image() -> None:
    with pytest.raises(ValidationError):
        ReadingBoundingBox(x=0.8, y=0.3, width=0.3, height=0.1)
