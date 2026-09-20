from hashlib import sha256

from sqlalchemy import select

from ai.pipeline.pipeline import DevelopmentPipeline
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.model_registry import ModelRecord

_cached_id = None
_cached_pipeline: DevelopmentPipeline | None = None


def _digest(path) -> str:
    builder = sha256()
    with path.open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            builder.update(chunk)
    return builder.hexdigest()


def current_pipeline() -> DevelopmentPipeline:
    global _cached_id, _cached_pipeline
    with SessionLocal() as db:
        record = db.scalar(
            select(ModelRecord)
            .where(
                ModelRecord.model_type == "meter_digit_centroid",
                ModelRecord.status == "ACTIVE",
            )
            .order_by(ModelRecord.activated_at.desc())
            .limit(1)
        )
    record_id = record.id if record else None
    if _cached_pipeline is not None and record_id == _cached_id:
        return _cached_pipeline
    if record is None:
        _cached_id = None
        _cached_pipeline = DevelopmentPipeline()
        return _cached_pipeline
    root = get_settings().models_root.resolve()
    path = (root / record.file_path).resolve()
    if (
        not path.is_relative_to(root)
        or not path.is_file()
        or _digest(path) != record.sha256
    ):
        raise ValueError("Model đang hoạt động không hợp lệ hoặc checksum không khớp.")
    _cached_id = record.id
    _cached_pipeline = DevelopmentPipeline(path, f"trained-{record.version}")
    return _cached_pipeline
