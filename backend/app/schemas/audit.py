from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditRow(BaseModel):
    id: UUID
    username: str | None
    action: str
    target_type: str | None
    target_id: str | None
    ip_address: str | None
    created_at: datetime
