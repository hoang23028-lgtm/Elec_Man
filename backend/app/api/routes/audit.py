from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.audit import AuditRow
from app.security.dependencies import get_current_user
from app.services.audit_service import list_audit_logs

router = APIRouter()


@router.get("", response_model=list[AuditRow])
def get_audit_logs(
    offset: int = 0,
    limit: int = 25,
    action: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AuditRow]:
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid pagination values."
        )
    normalized_action = action.strip().upper()[:64] if action else None
    return list_audit_logs(db, offset, limit, normalized_action)
