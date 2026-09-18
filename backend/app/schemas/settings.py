from datetime import datetime

from pydantic import BaseModel, Field

type SettingValue = str | int | float | bool | None


class SettingRow(BaseModel):
    key: str
    value: SettingValue
    description: str
    updated_at: datetime


class SettingsUpdate(BaseModel):
    values: dict[str, SettingValue] = Field(min_length=1, max_length=20)
