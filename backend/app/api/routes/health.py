from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return HealthResponse(status="ok", service="backend")


@router.get("/ready", response_model=HealthResponse)
def readiness(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cơ sở dữ liệu không khả dụng.",
        ) from exc
    return HealthResponse(status="ok", service="backend", database="ok")
