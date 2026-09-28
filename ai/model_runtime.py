from hashlib import sha256

from sqlalchemy import select

from ai.pipeline.pipeline import DevelopmentPipeline
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.model_registry import ModelRecord

_cached_ids: tuple[object | None, object | None] | None = None
_cached_pipeline: DevelopmentPipeline | None = None
SUPPORTED_METER_MODEL_TYPES = (
    "meter_digit_hog_softmax",
    "meter_digit_centroid",
)
SUPPORTED_REGION_MODEL_TYPES = ("reading_region_ridge",)


def _digest(path) -> str:
    builder = sha256()
    with path.open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            builder.update(chunk)
    return builder.hexdigest()


def _verified_path(record: ModelRecord | None):
    if record is None:
        return None
    root = get_settings().models_root.resolve()
    path = (root / record.file_path).resolve()
    if (
        not path.is_relative_to(root)
        or not path.is_file()
        or _digest(path) != record.sha256
    ):
        raise ValueError("Model đang hoạt động không hợp lệ hoặc checksum không khớp.")
    return path


def current_pipeline() -> DevelopmentPipeline:
    global _cached_ids, _cached_pipeline
    with SessionLocal() as db:
        digit_record = db.scalar(
            select(ModelRecord)
            .where(
                ModelRecord.model_type.in_(SUPPORTED_METER_MODEL_TYPES),
                ModelRecord.status == "ACTIVE",
            )
            .order_by(ModelRecord.activated_at.desc())
            .limit(1)
        )
        region_record = db.scalar(
            select(ModelRecord)
            .where(
                ModelRecord.model_type.in_(SUPPORTED_REGION_MODEL_TYPES),
                ModelRecord.status == "ACTIVE",
            )
            .order_by(ModelRecord.activated_at.desc())
            .limit(1)
        )
    record_ids = (
        digit_record.id if digit_record else None,
        region_record.id if region_record else None,
    )
    if _cached_pipeline is not None and record_ids == _cached_ids:
        return _cached_pipeline
    if digit_record is None and region_record is None:
        _cached_ids = record_ids
        _cached_pipeline = DevelopmentPipeline()
        return _cached_pipeline
    digit_path = _verified_path(digit_record)
    region_path = _verified_path(region_record)
    versions = "+".join(
        record.version for record in (digit_record, region_record) if record is not None
    )
    _cached_ids = record_ids
    _cached_pipeline = DevelopmentPipeline(
        digit_path,
        f"four-stage-{versions}",
        region_path,
    )
    return _cached_pipeline
