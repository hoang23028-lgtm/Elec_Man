from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.evaluation import EvaluationSummary
from app.security.dependencies import get_current_user
from app.services.evaluation_service import evaluation_summary

router = APIRouter()


@router.get("/summary", response_model=EvaluationSummary)
def get_evaluation_summary(
    model_version: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> EvaluationSummary:
    return evaluation_summary(db, model_version)
