from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DatasetAnnotationRequest(BaseModel):
    expected_revision: int = Field(ge=0)
    expected_label_revision: int = Field(ge=1)
    group_key: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    partition: Literal["UNASSIGNED", "TRAIN", "VALIDATION", "HOLDOUT"] = "UNASSIGNED"
    identity_verified: bool = False
    label_verified: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("group_key", mode="before")
    @classmethod
    def normalize_group(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def check_group(self):
        if (self.identity_verified or self.partition != "UNASSIGNED") and not self.group_key:
            raise ValueError("Cần mã nhóm công tơ trước khi xác minh hoặc phân tập.")
        return self


class TrainingStartRequest(BaseModel):
    experimental: bool = False
    fine_tune_reader: bool = True
    benchmark_deep_locator: bool = False
    deep_locator_epochs: int = Field(default=40, ge=1, le=100)
    epochs: int = Field(default=10, ge=1, le=100)
    batch_size: int = Field(default=8, ge=1, le=64)
    learning_rate: float = Field(default=0.0001, gt=0, le=0.01)
