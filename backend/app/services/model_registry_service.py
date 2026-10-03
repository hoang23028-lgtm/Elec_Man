from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.model_registry import ModelRecord
from app.models.user import User
from app.schemas.model_registry import ModelCreate, ModelRow

READING_REGION_MODEL_TYPES = {"reading_region_ridge"}
METER_LOCATOR_MODEL_TYPES = {"meter_locator_ridge"}
SUPPORTED_MODEL_TYPES = READING_REGION_MODEL_TYPES | METER_LOCATOR_MODEL_TYPES


def _row(record: ModelRecord) -> ModelRow:
    return ModelRow(
        id=record.id,
        model_name=record.model_name,
        model_type=record.model_type,
        version=record.version,
        file_path=record.file_path,
        metrics=record.metrics_json,
        status=record.status,
        sha256=record.sha256,
        created_at=record.created_at,
        activated_at=record.activated_at,
    )


def list_models(db: Session) -> list[ModelRow]:
    return [
        _row(record)
        for record in db.scalars(select(ModelRecord).order_by(ModelRecord.created_at.desc()))
    ]


def _verified_model_path(relative_path: str, claimed_sha256: str) -> Path:
    root = get_settings().models_root.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Tệp mô hình không khả dụng.",
        )
    digest_builder = sha256()
    with candidate.open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            digest_builder.update(chunk)
    digest = digest_builder.hexdigest()
    if digest.casefold() != claimed_sha256.casefold():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Mã kiểm tra của mô hình không khớp.",
        )
    return candidate


def _validate_activation_metrics(record: ModelRecord) -> None:
    if record.model_type in METER_LOCATOR_MODEL_TYPES:
        meter_accuracy = float(record.metrics_json.get("validation_meter_region_accuracy") or 0)
        if meter_accuracy < 0.8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Model định vị công tơ chỉ được kích hoạt khi độ chính xác đạt ít nhất 80%.",
            )
        return
    if record.model_type in READING_REGION_MODEL_TYPES:
        region_accuracy = float(record.metrics_json.get("validation_region_accuracy") or 0)
        if region_accuracy < 0.8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Model vùng chỉ số chỉ được kích hoạt khi độ chính xác đạt ít nhất 80%.",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Loại model này không còn được pipeline hiện tại hỗ trợ.",
    )


def register_model(
    db: Session, payload: ModelCreate, user: User, ip_address: str | None
) -> ModelRow:
    if payload.model_type not in SUPPORTED_MODEL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Loại mô hình không được pipeline hiện tại hỗ trợ.",
        )
    _verified_model_path(payload.file_path, payload.sha256)
    record = ModelRecord(
        model_name=payload.model_name.strip(),
        model_type=payload.model_type,
        version=payload.version,
        file_path=payload.file_path,
        metrics_json=payload.metrics,
        status="TESTING",
        sha256=payload.sha256.lower(),
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.add(
        AuditLog(
            user_id=user.id,
            action="REGISTER_MODEL",
            target_type="model",
            target_id=f"{record.model_name}:{record.version}",
            details_json={"model_type": record.model_type, "sha256": record.sha256},
            ip_address=ip_address,
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tên và phiên bản mô hình đã tồn tại.",
        ) from exc
    db.refresh(record)
    return _row(record)


def activate_model(db: Session, model_id: object, user: User, ip_address: str | None) -> ModelRow:
    record = db.get(ModelRecord, model_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mô hình.")
    _verified_model_path(record.file_path, record.sha256)
    _validate_activation_metrics(record)
    previous_status = record.status
    model_types = (
        READING_REGION_MODEL_TYPES
        if record.model_type in READING_REGION_MODEL_TYPES
        else METER_LOCATOR_MODEL_TYPES
        if record.model_type in METER_LOCATOR_MODEL_TYPES
        else {record.model_type}
    )
    db.execute(
        update(ModelRecord)
        .where(ModelRecord.model_type.in_(model_types), ModelRecord.status == "ACTIVE")
        .values(status="ARCHIVED")
    )
    record.status = "ACTIVE"
    record.activated_at = datetime.now(UTC)
    db.add(
        AuditLog(
            user_id=user.id,
            action="ACTIVATE_MODEL",
            target_type="model",
            target_id=str(record.id),
            details_json={
                "model_name": record.model_name,
                "model_type": record.model_type,
                "version": record.version,
                "previous_status": previous_status,
                "new_status": "ACTIVE",
                "sha256": record.sha256,
                "metrics": record.metrics_json,
            },
            ip_address=ip_address,
        )
    )
    db.commit()
    db.refresh(record)
    return _row(record)
