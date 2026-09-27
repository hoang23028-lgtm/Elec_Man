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
    ai_reading_bbox: ReadingBoundingBox | None


class ReviewRequest(BaseModel):
    final_customer_id: str | None = Field(default=None, max_length=128)
    final_meter_reading: str | None = Field(default=None, max_length=64)
    action: str = Field(pattern="^(CONFIRM|REJECT)$")
    reason: str | None = Field(default=None, max_length=1000)
    reading_bbox: ReadingBoundingBox | None = None


class ReviewResponse(BaseModel):
    image_id: UUID
    review_status: str
    reviewed_at: datetime


class RecognitionRequest(BaseModel):
    reading_bbox: ReadingBoundingBox


class RecognitionResponse(BaseModel):
    image_id: UUID
    job_id: UUID
    status: str


class RecognitionStatusResponse(RecognitionResponse):
    meter_reading_ai: str | None
    meter_confidence: float | None
    error_message: str | None
