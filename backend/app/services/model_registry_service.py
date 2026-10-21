from datetime import UTC, datetime
from hashlib import sha256
from math import isfinite
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.meter_reading import MeterReading
from app.models.model_registry import ModelRecord
from app.models.training_run import TrainingRun
from app.models.user import User
from app.schemas.model_registry import ModelCreate, ModelRow
from app.services.dataset_policy import sample_issues
from app.services.dataset_service import dataset_samples, lock_dataset

READING_REGION_MODEL_TYPES = {"reading_region_ridge", "reading_region_mobilenetv3"}
METER_LOCATOR_MODEL_TYPES = {"meter_locator_ridge", "meter_locator_mobilenetv3"}
READER_MODEL_TYPES = {"parseq_tiny_finetuned"}
SUPPORTED_MODEL_TYPES = READING_REGION_MODEL_TYPES | METER_LOCATOR_MODEL_TYPES | READER_MODEL_TYPES
MODEL_ACTIVATION_LOCK = 73051028


def _row(record: ModelRecord) -> ModelRow:
    return ModelRow(
        id=record.id,
        model_name=record.model_name,
        model_type=record.model_type,
        version=record.version,
        file_path=record.file_path,
        metrics={
            key: value for key, value in record.metrics_json.items() if key != "dataset_snapshot"
        },
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
    metrics = record.metrics_json
    if (
        metrics.get("independent_holdout") is not True
        or metrics.get("end_to_end_evaluated") is not True
        or isinstance(metrics.get("holdout_images"), bool)
        or not isinstance(metrics.get("holdout_images"), int)
        or metrics["holdout_images"] < 30
    ):
        raise HTTPException(422, "Cần ít nhất 30 ảnh holdout độc lập được đánh giá toàn quy trình.")
    if metrics.get("validation_groups_verified") is not True or (
        not isinstance(metrics.get("validation_images"), int)
        or isinstance(metrics.get("validation_images"), bool)
        or metrics["validation_images"] < 30
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Cần ít nhất 30 ảnh kiểm định tách theo nhóm công tơ "
                "đã xác minh trước khi kích hoạt."
            ),
        )

    def validated_score(key):
        value = metrics.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(value):
            return 0.0
        return float(value) if 0 <= value <= 1 else 0.0

    e2e = metrics.get("holdout_end_to_end") or {}
    if not isinstance(e2e, dict):
        raise HTTPException(422, "Kết quả kiểm định toàn quy trình không hợp lệ.")
    if record.model_type in READING_REGION_MODEL_TYPES | METER_LOCATOR_MODEL_TYPES:
        value = e2e.get(
            "meter_mean_iou"
            if record.model_type in METER_LOCATOR_MODEL_TYPES
            else "reading_mean_iou"
        )
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not isfinite(value)
            or not 0.8 <= value <= 1
        ):
            raise HTTPException(422, "IoU vùng trên holdout toàn quy trình phải đạt ít nhất 0,8.")
    if record.model_type.endswith("mobilenetv3"):
        comparison = metrics.get("locator_benchmark") or {}
        if not isinstance(comparison, dict):
            raise HTTPException(422, "Benchmark định vị không hợp lệ.")
        baseline = comparison.get("ridge_end_to_end") or {}
        if not isinstance(baseline, dict):
            raise HTTPException(422, "Đối chứng Ridge không hợp lệ.")
        key = (
            "meter_mean_iou"
            if record.model_type in METER_LOCATOR_MODEL_TYPES
            else "reading_mean_iou"
        )
        if (
            comparison.get("independent_holdout") is not True
            or baseline.get("evaluation_complete") is not True
            or any(
                isinstance(baseline.get(k), bool)
                or not isinstance(baseline.get(k), int | float)
                or not isfinite(baseline[k])
                or not 0 <= baseline[k] <= 1
                for k in (key, "exact_accuracy", "coverage")
            )
            or e2e.get(key, 0) <= baseline[key]
            or any(
                not isinstance(e2e.get(k), int | float)
                or isinstance(e2e.get(k), bool)
                or not isfinite(e2e[k])
                or not baseline[k] <= e2e[k] <= 1
                for k in ("exact_accuracy", "coverage")
            )
        ):
            raise HTTPException(
                422,
                "Ứng viên học sâu phải tăng IoU và không giảm độ chính xác/độ phủ "
                "so với Ridge trên cùng holdout.",
            )
    if record.model_type in READER_MODEL_TYPES:
        reading = metrics.get("holdout_reader") or {}
        if not isinstance(reading, dict):
            raise HTTPException(422, "Kết quả kiểm định bộ đọc không hợp lệ.")
        for score_key in ("exact_accuracy", "coverage"):
            value = reading.get(score_key)
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not isfinite(value)
                or not 0.95 <= value <= 1
            ):
                raise HTTPException(
                    422, "Bộ đọc cần đúng toàn chuỗi và độ phủ ít nhất 95% trên holdout."
                )
        for key in ("exact_accuracy", "coverage"):
            value = e2e.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not isfinite(value)
                or not 0.9 <= value <= 1
            ):
                raise HTTPException(
                    422, "Toàn quy trình cần đúng toàn chuỗi và độ phủ ít nhất 90%."
                )
        return

    if record.model_type in METER_LOCATOR_MODEL_TYPES:
        meter_accuracy = validated_score("validation_meter_region_accuracy")
        if meter_accuracy < 0.8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Mô hình định vị công tơ cần điểm đánh giá vùng tối thiểu 0,8 để kích hoạt.",
            )
        return
    if record.model_type in READING_REGION_MODEL_TYPES:
        region_accuracy = validated_score("validation_region_accuracy")
        if region_accuracy < 0.8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Mô hình vùng chỉ số cần điểm đánh giá vùng tối thiểu 0,8 để kích hoạt.",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Loại model này không còn được pipeline hiện tại hỗ trợ.",
    )


def _validate_training_provenance(db, record):
    try:
        run_id = UUID(record.metrics_json.get("training_run_id", ""))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            422, "Thiếu phiên huấn luyện/kiểm định do hệ thống thực hiện."
        ) from None
    run = db.get(TrainingRun, run_id)
    metrics = run.metrics_json if run and run.status == "COMPLETED" else {}
    if (
        str(record.id) not in metrics.get("artifact_ids", [])
        or metrics.get("artifact_sha256", {}).get(str(record.id)) != record.sha256
        or not run
        or run.dataset_hash != record.metrics_json.get("dataset_hash")
    ):
        raise HTTPException(422, "Artifact không thuộc kết quả kiểm định đã hoàn tất của hệ thống.")
    holdout = metrics.get("dataset_snapshot", {}).get("partitions", {}).get("HOLDOUT", [])
    if len(holdout) < 30:
        raise HTTPException(422, "Không có snapshot holdout đủ mẫu.")
    db.scalars(
        select(MeterReading)
        .where(MeterReading.image_id.in_([UUID(s["image"]["id"]) for s in holdout]))
        .order_by(MeterReading.image_id)
        .with_for_update()
    ).all()
    current = {s["image"]["id"]: s for s in dataset_samples(db)}
    for sample in holdout:
        now = current.get(sample["image"]["id"])
        if (
            not now
            or sample_issues(now)
            or now["image"]["sha256"] != sample["image"]["sha256"]
            or now["reading"]["revision"] != sample["reading"]["revision"]
            or now["annotation"].get("partition") != "HOLDOUT"
            or now["annotation"].get("group_key") != sample["annotation"].get("group_key")
        ):
            raise HTTPException(
                422, "Nhãn/nhóm holdout đã thay đổi sau kiểm định. Cần đánh giá lại."
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
    # Serialize activation before reading/archive updates: two admins must not
    # leave two ACTIVE models of the same type after simultaneous requests.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": MODEL_ACTIVATION_LOCK})
    record = db.get(ModelRecord, model_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mô hình.")
    _verified_model_path(record.file_path, record.sha256)
    _validate_activation_metrics(record)
    lock_dataset(db)
    _validate_training_provenance(db, record)
    if (
        record.model_type in READING_REGION_MODEL_TYPES
        and record.metrics_json.get("coordinate_space") == "meter"
    ):
        compatible_meter = db.scalar(
            select(ModelRecord.id).where(
                ModelRecord.model_type.in_(METER_LOCATOR_MODEL_TYPES),
                ModelRecord.version == record.version,
                ModelRecord.status == "ACTIVE",
                ModelRecord.model_type
                == (
                    "meter_locator_mobilenetv3"
                    if record.model_type.endswith("mobilenetv3")
                    else "meter_locator_ridge"
                ),
            )
        )
        if compatible_meter is None:
            raise HTTPException(422, "Kích hoạt định vị công tơ cùng phiên bản trước vùng chỉ số.")
    previous_status = record.status
    if record.model_type in READER_MODEL_TYPES:
        active = db.scalars(
            select(ModelRecord).where(
                ModelRecord.model_type.in_(READING_REGION_MODEL_TYPES | METER_LOCATOR_MODEL_TYPES),
                ModelRecord.status == "ACTIVE",
                ModelRecord.version == record.version,
            )
        ).all()
        family = record.metrics_json.get("locator_family", "ridge")
        if {r.model_type for r in active} != {
            f"meter_locator_{family}",
            f"reading_region_{family}",
        }:
            raise HTTPException(422, "Kích hoạt hai bộ định vị cùng phiên bản trước bộ đọc.")
    model_types = (
        READING_REGION_MODEL_TYPES
        if record.model_type in READING_REGION_MODEL_TYPES
        else METER_LOCATOR_MODEL_TYPES
        if record.model_type in METER_LOCATOR_MODEL_TYPES
        else READER_MODEL_TYPES
        if record.model_type in READER_MODEL_TYPES
        else {record.model_type}
    )
    db.execute(
        update(ModelRecord)
        .where(ModelRecord.model_type.in_(model_types), ModelRecord.status == "ACTIVE")
        .values(status="ARCHIVED")
    )
    record.status = "ACTIVE"
    if record.model_type in METER_LOCATOR_MODEL_TYPES:
        db.execute(
            update(ModelRecord)
            .where(
                ModelRecord.model_type.in_(READING_REGION_MODEL_TYPES),
                ModelRecord.status == "ACTIVE",
                (
                    (ModelRecord.version != record.version)
                    | (
                        ModelRecord.model_type
                        != (
                            "reading_region_mobilenetv3"
                            if record.model_type.endswith("mobilenetv3")
                            else "reading_region_ridge"
                        )
                    )
                ),
                ModelRecord.metrics_json["coordinate_space"].as_string() == "meter",
            )
            .values(status="ARCHIVED")
        )
    if record.model_type in METER_LOCATOR_MODEL_TYPES | READING_REGION_MODEL_TYPES:
        db.execute(
            update(ModelRecord)
            .where(
                ModelRecord.model_type.in_(READER_MODEL_TYPES),
                ModelRecord.status == "ACTIVE",
                (
                    (ModelRecord.version != record.version)
                    | (
                        func.coalesce(
                            ModelRecord.metrics_json["locator_family"].as_string(), "ridge"
                        )
                        != ("mobilenetv3" if record.model_type.endswith("mobilenetv3") else "ridge")
                    )
                ),
            )
            .values(status="ARCHIVED")
        )
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
