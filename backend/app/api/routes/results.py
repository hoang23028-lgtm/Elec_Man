from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.result import ResultRow, ReviewRequest, ReviewResponse
from app.security.dependencies import get_current_user, require_csrf
from app.services.review_service import list_results, review_result
router = APIRouter()

@router.get("", response_model=list[ResultRow])
def get_results(offset: int = 0, limit: int = 50, image_status: str | None = None, search: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ResultRow]:
    if offset < 0 or not 1 <= limit <= 100: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid pagination values.")
    return list_results(db, offset, limit, image_status, search)

@router.put("/{image_id}/review", response_model=ReviewResponse, dependencies=[Depends(require_csrf)])
def review(image_id: UUID, payload: ReviewRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ReviewResponse:
    record = review_result(db, image_id, payload, user, request.client.host if request.client else None)
    return ReviewResponse(image_id=image_id, review_status=record.review_status, reviewed_at=record.reviewed_at)
