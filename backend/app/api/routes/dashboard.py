from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.security.dependencies import get_current_user
from app.services.dashboard_service import statistics

router = APIRouter()


@router.get("")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    return statistics(db)
