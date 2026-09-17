from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateBatchRequest(BaseModel):
    original_folder_name: str = Field(min_length=1, max_length=255)


class BatchResponse(BaseModel):
    id: UUID
    batch_code: str
    original_folder_name: str
    status: str
    total_images: int
    uploaded_images: int
    processed_images: int
    review_count: int
    failed_count: int
    created_at: datetime


class UploadedImageResponse(BaseModel):
    id: UUID
    original_filename: str
    status: str
    duplicate: bool = False
