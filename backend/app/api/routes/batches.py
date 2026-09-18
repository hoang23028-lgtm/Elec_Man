from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.batch import BatchResponse, CreateBatchRequest, UploadedImageResponse
from app.security.dependencies import get_current_user, require_csrf
from app.services.batch_service import create_batch, list_batches, save_uploaded_image
from app.services.storage_service import store_upload

router = APIRouter()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_batch_route(
    payload: CreateBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BatchResponse:
    return create_batch(db, payload.original_folder_name, user, _ip(request))


@router.get("", response_model=list[BatchResponse])
def list_batches_route(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[BatchResponse]:
    if offset < 0 or not 1 <= limit <= 100:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid pagination values."
        )
    return list_batches(db, offset, limit)


@router.post(
    "/{batch_id}/images",
    response_model=UploadedImageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def upload_image_route(
    batch_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadedImageResponse:
    upload = await store_upload(file, batch_id)
    image = save_uploaded_image(db, batch_id, upload, user, _ip(request))
    return UploadedImageResponse(
        id=image.id, original_filename=image.original_filename, status=image.status
    )
