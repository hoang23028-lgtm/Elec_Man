from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResultRow(BaseModel):
    image_id: UUID
    original_filename: str
    image_status: str
    ai_result_id: UUID
    customer_id_ai: str | None
    meter_reading_ai: str | None
    final_confidence: float
    ai_status: str
    review_status: str | None
    final_customer_id: str | None
    final_meter_reading: str | None


class ReviewRequest(BaseModel):
    final_customer_id: str | None = Field(default=None, max_length=128)
    final_meter_reading: str | None = Field(default=None, max_length=64)
    action: str = Field(pattern="^(CONFIRM|REJECT)$")
    reason: str | None = Field(default=None, max_length=1000)


class ReviewResponse(BaseModel):
    image_id: UUID
    review_status: str
    reviewed_at: datetime
