import pytest
from pydantic import ValidationError

from app.schemas.result import ReadingBoundingBox, ReadingPolygon, ReviewRequest


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


def test_reading_polygon_accepts_four_ordered_points() -> None:
    polygon = ReadingPolygon(
        points=[
            {"x": 0.2, "y": 0.3},
            {"x": 0.8, "y": 0.25},
            {"x": 0.75, "y": 0.5},
            {"x": 0.25, "y": 0.55},
        ]
    )

    assert polygon.bounding_box() == ReadingBoundingBox(x=0.2, y=0.25, width=0.6, height=0.3)


def test_reading_polygon_rejects_crossed_edges() -> None:
    with pytest.raises(ValidationError):
        ReadingPolygon(
            points=[
                {"x": 0.2, "y": 0.2},
                {"x": 0.8, "y": 0.8},
                {"x": 0.8, "y": 0.2},
                {"x": 0.2, "y": 0.8},
            ]
        )


def test_reading_polygon_rejects_concave_region() -> None:
    with pytest.raises(ValidationError):
        ReadingPolygon(
            points=[
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.4, "y": 0.4},
                {"x": 0.1, "y": 0.9},
            ]
        )
