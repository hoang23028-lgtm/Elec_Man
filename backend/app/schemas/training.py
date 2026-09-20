from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DatasetSummary(BaseModel):
    uploaded_images: int
    confirmed_images: int
    eligible_samples: int
    minimum_samples: int
    new_samples_since_last_run: int
    auto_start_enabled: bool
    ready: bool


class TrainingRunRow(BaseModel):
    id: UUID
    status: str
    trigger: str
    stage: str
    progress: int
    sample_count: int
    training_count: int
    validation_count: int
    dataset_hash: str | None
    metrics: dict
    error_message: str | None
    model_id: UUID | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class TrainingOverview(BaseModel):
    dataset: DatasetSummary
    runs: list[TrainingRunRow]
