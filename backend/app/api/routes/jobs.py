from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.batch import BatchResponse
from app.security.dependencies import get_current_user, require_csrf
from app.services.job_service import queue_batch

router = APIRouter()


@router.post("/batches/{batch_id}/start", response_model=BatchResponse, dependencies=[Depends(require_csrf)])
def start_batch(batch_id: UUID, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> BatchResponse:
    ip_address = request.client.host if request.client else None
    return queue_batch(db, batch_id, user, ip_address)
