from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=128)
    model_type: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    file_path: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    metrics: dict = Field(default_factory=dict)


class ModelRow(BaseModel):
    id: UUID
    model_name: str
    model_type: str
    version: str
    file_path: str
    metrics: dict
    status: str
    sha256: str
    created_at: datetime
    activated_at: datetime | None
