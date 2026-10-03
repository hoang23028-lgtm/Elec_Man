from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.pagination import validate_pagination
from app.core.database import get_db
from app.models.image import ImageStatus
from app.models.user import User
from app.schemas.result import (
    MeterRegionRequest,
    MeterRegionResponse,
    RecognitionRequest,
    RecognitionResponse,
    RecognitionStatusResponse,
    ResultRow,
    ResultStatusCounts,
    ReviewRequest,
    ReviewResponse,
    TrainingLabelRequest,
)
from app.security.dependencies import get_current_user, require_csrf
from app.services.region_recognition_service import (
    queue_region_recognition,
    region_recognition_status,
    save_meter_region,
    save_training_label,
)
from app.services.review_service import get_result_status_counts, list_results, review_result

router = APIRouter()


@router.get("/status-counts", response_model=ResultStatusCounts)
def status_counts(
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ResultStatusCounts:
    return get_result_status_counts(db, search)


@router.put(
    "/{image_id}/meter-region",
    response_model=MeterRegionResponse,
    dependencies=[Depends(require_csrf)],
)
def meter_region(
    image_id: UUID,
    payload: MeterRegionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeterRegionResponse:
    reading = save_meter_region(
        db,
        image_id,
        payload.meter_polygon,
        user,
        request.client.host if request.client else None,
    )
    return MeterRegionResponse(
        image_id=image_id,
        meter_polygon=reading.meter_polygon_json,
        saved_at=reading.meter_bbox_reviewed_at,
    )


@router.get("", response_model=list[ResultRow])
def get_results(
    response: Response,
    offset: int = 0,
    limit: int = 50,
    image_status: ImageStatus | None = None,
    search: str | None = None,
    review_status: Literal["PENDING", "LABELED", "CONFIRMED", "REJECTED"] | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ResultRow]:
    validate_pagination(offset, limit)
    rows, total = list_results(db, offset, limit, image_status, search, review_status)
    response.headers["X-Total-Count"] = str(total)
    return rows


@router.put(
    "/{image_id}/review", response_model=ReviewResponse, dependencies=[Depends(require_csrf)]
)
def review(
    image_id: UUID,
    payload: ReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReviewResponse:
    record = review_result(
        db, image_id, payload, user, request.client.host if request.client else None
    )
    return ReviewResponse(
        image_id=image_id, review_status=record.review_status, reviewed_at=record.reviewed_at
    )


@router.post(
    "/{image_id}/recognize-reading",
    response_model=RecognitionResponse,
    status_code=202,
    dependencies=[Depends(require_csrf)],
)
def recognize_reading(
    image_id: UUID,
    payload: RecognitionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecognitionResponse:
    return queue_region_recognition(
        db,
        image_id,
        payload.reading_polygon,
        user,
        request.client.host if request.client else None,
        integer_digits=payload.integer_digits,
    )


@router.get("/{image_id}/recognize-reading", response_model=RecognitionStatusResponse)
def recognize_reading_status(
    image_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> RecognitionStatusResponse:
    return region_recognition_status(db, image_id)


@router.post(
    "/{image_id}/training-label",
    response_model=ReviewResponse,
    dependencies=[Depends(require_csrf)],
)
def training_label(
    image_id: UUID,
    payload: TrainingLabelRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReviewResponse:
    reading = save_training_label(
        db,
        image_id,
        payload.final_meter_reading,
        payload.reading_polygon,
        payload.meter_polygon,
        user,
        request.client.host if request.client else None,
    )
    return ReviewResponse(
        image_id=image_id,
        review_status=reading.review_status,
        reviewed_at=reading.reviewed_at,
    )
