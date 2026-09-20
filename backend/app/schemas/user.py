from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

USERNAME_PATTERN = r"^[A-Za-z0-9._-]+$"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=12, max_length=256)
    is_active: bool = True

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()


class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=64, pattern=USERNAME_PATTERN
    )
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "UserUpdate":
        if self.username is None and self.is_active is None:
            raise ValueError("Cần cung cấp ít nhất một thay đổi.")
        return self


class PasswordUpdate(BaseModel):
    new_password: str = Field(min_length=12, max_length=256)


class UserRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
