from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.batch import Batch, BatchStatus
from app.models.image import ImageRecord
from app.models.user import User
from app.services.storage_service import StoredUpload, delete_stored_upload


def create_batch(
    db: Session, original_folder_name: str, user: User, ip_address: str | None
) -> Batch:
    folder_name = original_folder_name.strip().replace("\\", "/").split("/")[-1][:255]
    if not folder_name or folder_name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid folder name."
        )
    identifier = uuid4()
    code = f"BATCH-{datetime.now(UTC):%Y%m%d}-{identifier.hex[:6].upper()}"
    batch = Batch(
        id=identifier,
        batch_code=code,
        original_folder_name=folder_name,
        status=BatchStatus.UPLOADING,
    )
    db.add(batch)
    db.add(
        AuditLog(
            user_id=user.id,
            action="CREATE_BATCH",
            target_type="batch",
            target_id=str(batch.id),
            details_json={"batch_code": code},
            ip_address=ip_address,
        )
    )
    db.commit()
    db.refresh(batch)
    return batch


def save_uploaded_image(
    db: Session, batch_id: UUID, upload: StoredUpload, user: User, ip_address: str | None
) -> ImageRecord:
    batch = db.get(Batch, batch_id)
    if batch is None:
        delete_stored_upload(upload)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    image = ImageRecord(
        batch_id=batch_id,
        original_filename=upload.original_filename,
        stored_filename=upload.stored_filename,
        relative_path=upload.relative_path,
        thumbnail_path=upload.thumbnail_path,
        file_size=upload.file_size,
        mime_type=upload.mime_type,
        sha256=upload.sha256,
        width=upload.width,
        height=upload.height,
    )
    counter_update = db.execute(
        update(Batch)
        .where(Batch.id == batch_id, Batch.status == BatchStatus.UPLOADING)
        .values(total_images=Batch.total_images + 1, uploaded_images=Batch.uploaded_images + 1)
    )
    if counter_update.rowcount != 1:
        db.rollback()
        delete_stored_upload(upload)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Batch no longer accepts uploads."
        )
    db.add(image)
    db.add(
        AuditLog(
            user_id=user.id,
            action="UPLOAD_IMAGE",
            target_type="image",
            target_id=str(image.id),
            details_json={"batch_id": str(batch.id), "sha256": upload.sha256},
            ip_address=ip_address,
        )
    )
    try:
        db.commit()
        db.refresh(image)
    except IntegrityError as exc:
        db.rollback()
        delete_stored_upload(upload)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Exact duplicate image in this batch."
        ) from exc
    except Exception:
        db.rollback()
        delete_stored_upload(upload)
        raise
    return image


def list_batches(db: Session, offset: int, limit: int) -> list[Batch]:
    return list(
        db.scalars(select(Batch).order_by(Batch.created_at.desc()).offset(offset).limit(limit))
    )
