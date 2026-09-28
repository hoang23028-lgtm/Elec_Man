from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReadingBoundingBox(BaseModel):
    """Normalized reading-register coordinates relative to the source image."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> "ReadingBoundingBox":
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("Vùng chỉ số phải nằm hoàn toàn bên trong ảnh.")
        return self


class ReadingPoint(BaseModel):
    """A normalized point relative to the source image."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class ReadingPolygon(BaseModel):
    """Four ordered corners of the reading register."""

    points: list[ReadingPoint] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_polygon(self) -> "ReadingPolygon":
        coordinates = [(point.x, point.y) for point in self.points]
        if len(set(coordinates)) != 4:
            raise ValueError("Bốn góc của vùng chỉ số phải khác nhau.")

        def orientation(a, b, c) -> float:
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        def crosses(a, b, c, d) -> bool:
            return (
                orientation(a, b, c) * orientation(a, b, d) < 0
                and orientation(c, d, a) * orientation(c, d, b) < 0
            )

        if crosses(coordinates[0], coordinates[1], coordinates[2], coordinates[3]) or crosses(
            coordinates[1], coordinates[2], coordinates[3], coordinates[0]
        ):
            raise ValueError("Các cạnh của vùng chỉ số không được cắt nhau.")
        turns = [
            orientation(
                coordinates[index],
                coordinates[(index + 1) % 4],
                coordinates[(index + 2) % 4],
            )
            for index in range(4)
        ]
        if not (all(turn > 0 for turn in turns) or all(turn < 0 for turn in turns)):
            raise ValueError("Vùng chỉ số phải là một tứ giác lồi.")
        area = (
            abs(
                sum(
                    x * coordinates[(index + 1) % 4][1] - y * coordinates[(index + 1) % 4][0]
                    for index, (x, y) in enumerate(coordinates)
                )
            )
            / 2
        )
        if area < 0.000025:
            raise ValueError("Vùng chỉ số quá nhỏ hoặc không hợp lệ.")
        return self

    def bounding_box(self) -> ReadingBoundingBox:
        left = min(point.x for point in self.points)
        top = min(point.y for point in self.points)
        right = max(point.x for point in self.points)
        bottom = max(point.y for point in self.points)
        return ReadingBoundingBox(
            x=left,
            y=top,
            width=round(right - left, 8),
            height=round(bottom - top, 8),
        )


class ResultRow(BaseModel):
    image_id: UUID
    original_filename: str
    image_width: int
    image_height: int
    image_status: str
    ai_result_id: UUID
    customer_id_ai: str | None
    meter_reading_ai: str | None
    final_confidence: float
    ai_status: str
    review_status: str | None
    auto_confirmed: bool
    final_customer_id: str | None
    final_meter_reading: str | None
    customer_match_status: str
    matched_customer_name: str | None
    matched_meter_serial: str | None
    reading_bbox: ReadingBoundingBox | None
    reading_polygon: ReadingPolygon | None
    ai_reading_bbox: ReadingBoundingBox | None


class ReviewRequest(BaseModel):
    final_customer_id: str | None = Field(default=None, max_length=128)
    final_meter_reading: str | None = Field(default=None, max_length=64)
    action: str = Field(pattern="^(CONFIRM|REJECT)$")
    reason: str | None = Field(default=None, max_length=1000)
    reading_bbox: ReadingBoundingBox | None = None
    reading_polygon: ReadingPolygon | None = None


class ReviewResponse(BaseModel):
    image_id: UUID
    review_status: str
    reviewed_at: datetime


class RecognitionRequest(BaseModel):
    reading_polygon: ReadingPolygon


class RecognitionResponse(BaseModel):
    image_id: UUID
    job_id: UUID
    status: str


class RecognitionStatusResponse(RecognitionResponse):
    meter_reading_ai: str | None
    meter_confidence: float | None
    error_message: str | None
