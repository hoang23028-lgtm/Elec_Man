from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.pagination import validate_pagination
from app.core.database import get_db
from app.models.user import User
from app.schemas.audit import AuditRow
from app.security.dependencies import get_current_user
from app.services.audit_service import list_audit_logs

router = APIRouter()


@router.get("", response_model=list[AuditRow])
def get_audit_logs(
    response: Response,
    offset: int = 0,
    limit: int = 25,
    action: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AuditRow]:
    validate_pagination(offset, limit)
    normalized_action = action.strip().upper()[:64] if action else None
    rows, total = list_audit_logs(db, offset, limit, normalized_action)
    response.headers["X-Total-Count"] = str(total)
    return rows
