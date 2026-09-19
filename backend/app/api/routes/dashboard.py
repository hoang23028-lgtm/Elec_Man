from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import BillingDashboard
from app.services.dashboard_service import billing_dashboard, statistics

router = APIRouter()


@router.get("")
def dashboard(db: Session = Depends(get_db)) -> dict:
    """Expose aggregate operational counts without exposing record-level data."""
    return statistics(db)


@router.get("/billing", response_model=BillingDashboard)
def dashboard_billing(
    customer_id: str | None = Query(default=None, max_length=128),
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
) -> BillingDashboard:
    """Expose confirmed readings and transparent bill estimates as read-only data."""
    return billing_dashboard(db, customer_id, month, year, offset, limit)
