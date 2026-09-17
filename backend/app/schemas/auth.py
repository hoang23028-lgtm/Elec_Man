from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    csrf_token: str
    expires_at: datetime


class CurrentUserResponse(BaseModel):
    id: UUID
    username: str
    last_login_at: datetime | None
