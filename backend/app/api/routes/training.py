from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.training import TrainingOverview, TrainingRunRow
from app.security.dependencies import AuthContext, get_current_user, require_csrf
from app.services.training_service import enqueue_training, overview

router = APIRouter()


@router.get("", response_model=TrainingOverview)
def get_training(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> TrainingOverview:
    return overview(db)


@router.post("/runs", response_model=TrainingRunRow, status_code=status.HTTP_202_ACCEPTED)
def start_training(
    request: Request, db: Session = Depends(get_db), auth: AuthContext = Depends(require_csrf)
) -> TrainingRunRow:
    return enqueue_training(
        db, "MANUAL", auth.user, request.client.host if request.client else None
    )
