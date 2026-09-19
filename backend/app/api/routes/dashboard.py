from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.dashboard_service import statistics

router = APIRouter()


@router.get("")
def dashboard(db: Session = Depends(get_db)) -> dict:
    """Expose aggregate operational counts without exposing record-level data."""
    return statistics(db)
