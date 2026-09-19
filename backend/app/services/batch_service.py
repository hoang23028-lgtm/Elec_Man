from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ai_result import AiResult
from app.models.audit_log import AuditLog
from app.models.batch import Batch, BatchStatus
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.schemas.batch import BatchImageResponse
from app.services.storage_service import StoredUpload, delete_stored_upload


def create_batch(
    db: Session, original_folder_name: str, user: User, ip_address: str | None
) -> Batch:
    folder_name = original_folder_name.strip().replace("\\", "/").split("/")[-1][:255]
    if not folder_name or folder_name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tên thư mục không hợp lệ.",
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lô dữ liệu."
        )
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
            status_code=status.HTTP_409_CONFLICT,
            detail="Lô dữ liệu này không còn nhận tệp tải lên.",
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
            status_code=status.HTTP_409_CONFLICT,
            detail="Ảnh này đã tồn tại trong lô dữ liệu.",
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


def count_batches(db: Session) -> int:
    return int(db.scalar(select(func.count(Batch.id))) or 0)


def list_batch_images(
    db: Session, batch_id: UUID, offset: int, limit: int
) -> list[BatchImageResponse]:
    if db.get(Batch, batch_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lô dữ liệu.",
        )
    statement = (
        select(ImageRecord, AiResult, MeterReading)
        .outerjoin(AiResult, AiResult.image_id == ImageRecord.id)
        .outerjoin(MeterReading, MeterReading.image_id == ImageRecord.id)
        .where(ImageRecord.batch_id == batch_id)
        .order_by(ImageRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [
        BatchImageResponse(
            image_id=image.id,
            original_filename=image.original_filename,
            image_status=image.status,
            width=image.width,
            height=image.height,
            file_size=image.file_size,
            created_at=image.created_at,
            customer_id_ai=ai_result.customer_id_ai if ai_result else None,
            meter_reading_ai=ai_result.meter_reading_ai if ai_result else None,
            final_confidence=ai_result.final_confidence if ai_result else None,
            review_status=reading.review_status if reading else None,
            final_customer_id=reading.final_customer_id if reading else None,
            final_meter_reading=reading.final_meter_reading if reading else None,
        )
        for image, ai_result, reading in db.execute(statement)
    ]


def count_batch_images(db: Session, batch_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count(ImageRecord.id)).where(ImageRecord.batch_id == batch_id)
        )
        or 0
    )
