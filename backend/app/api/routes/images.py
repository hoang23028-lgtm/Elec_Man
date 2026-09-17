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


@router.get("/{image_id}/preview")
def preview_image(image_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> FileResponse:
    image = db.get(ImageRecord, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")
    return FileResponse(resolve_storage_path(image.relative_path), media_type=image.mime_type, filename="preview")
