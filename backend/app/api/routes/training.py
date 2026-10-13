from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.training_run import TrainingRun
from app.models.user import User
from app.schemas.dataset import DatasetAnnotationRequest, TrainingStartRequest
from app.schemas.training import TrainingOverview, TrainingRunRow
from app.security.dependencies import AuthContext, get_current_user, require_csrf
from app.services.dataset_service import data_overview, save_annotation
from app.services.operational_health import health_overview
from app.services.training_service import enqueue_training, overview

router = APIRouter()


@router.get("/health")
def get_operational_health(db: Session = Depends(get_db)):
    return health_overview(db)


@router.get("", response_model=TrainingOverview)
def get_training(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> TrainingOverview:
    return overview(db)


@router.post("/runs", response_model=TrainingRunRow, status_code=status.HTTP_202_ACCEPTED)
def start_training(
    request: Request,
    payload: TrainingStartRequest = TrainingStartRequest(),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
) -> TrainingRunRow:
    return enqueue_training(
        db,
        "MANUAL",
        auth.user,
        request.client.host if request.client else None,
        experimental=payload.experimental,
        options=payload.model_dump(exclude={"experimental"}),
    )


@router.get("/data")
def get_data(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=12, ge=1, le=100),
    search: str = Query(default="", max_length=255),
    db: Session = Depends(get_db),
):
    return data_overview(db, offset, limit, search)


@router.put("/data/{image_id}")
def update_data(
    image_id: UUID,
    payload: DatasetAnnotationRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
):
    return save_annotation(
        db, image_id, payload, auth.user, request.client.host if request.client else None
    )


@router.post("/runs/{run_id}/cancel")
def cancel_training(
    run_id: UUID, db: Session = Depends(get_db), auth: AuthContext = Depends(require_csrf)
):
    run = db.scalar(select(TrainingRun).where(TrainingRun.id == run_id).with_for_update())
    if run is None or run.status not in {"PENDING", "RUNNING"}:
        raise HTTPException(409, "Phiên không còn ở trạng thái có thể hủy.")
    previous = run.status
    run.status, run.stage, run.completed_at = "CANCELLED", "CANCELLED", datetime.now(UTC)
    db.add(
        AuditLog(
            user_id=auth.user.id,
            action="TRAINING_CANCELLED",
            target_type="training_run",
            target_id=str(run_id),
            details_json={"previous_status": previous, "new_status": "CANCELLED"},
            ip_address=None,
        )
    )
    db.commit()
    return {"id": run_id, "status": "CANCELLED"}
