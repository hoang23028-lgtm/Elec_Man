from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.image import ImageRecord
from app.models.user import User
from app.security.dependencies import get_current_user
from app.services.storage_service import resolve_storage_path

router = APIRouter()
IMMUTABLE_IMAGE_HEADERS = {"Cache-Control": "private, max-age=86400, immutable"}


@router.get("/{image_id}/preview")
def preview_image(
    image_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> FileResponse:
    image = db.get(ImageRecord, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ảnh.")
    return FileResponse(
        resolve_storage_path(image.relative_path),
        media_type=image.mime_type,
        filename="preview",
        headers=IMMUTABLE_IMAGE_HEADERS,
    )


@router.get("/{image_id}/thumbnail")
def thumbnail_image(
    image_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> FileResponse:
    image = db.get(ImageRecord, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ảnh.")
    return FileResponse(
        resolve_storage_path(image.thumbnail_path),
        media_type="image/jpeg",
        filename="thumbnail.jpg",
        headers=IMMUTABLE_IMAGE_HEADERS,
    )
