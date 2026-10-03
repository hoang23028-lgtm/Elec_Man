from hashlib import sha256

from sqlalchemy import select

from ai.pipeline.meter_pipeline import MeterReadingPipeline
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.model_registry import ModelRecord

_cached_ids: tuple[object | None, object | None] | None = None
_cached_pipeline: MeterReadingPipeline | None = None
SUPPORTED_REGION_MODEL_TYPES = ("reading_region_ridge",)
SUPPORTED_METER_LOCATOR_MODEL_TYPES = ("meter_locator_ridge",)


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


def current_pipeline() -> MeterReadingPipeline:
    global _cached_ids, _cached_pipeline
    with SessionLocal() as db:
        records = db.scalars(
            select(ModelRecord)
            .where(
                ModelRecord.model_type.in_(
                    SUPPORTED_REGION_MODEL_TYPES + SUPPORTED_METER_LOCATOR_MODEL_TYPES
                ),
                ModelRecord.status == "ACTIVE",
            )
            .order_by(ModelRecord.activated_at.desc())
        ).all()
        # One round trip; newest active artifact in each supported family.
        # No TTL: activations remain visible on the very next job.
        region_record = next(
            (r for r in records if r.model_type in SUPPORTED_REGION_MODEL_TYPES), None
        )
        meter_record = next(
            (r for r in records if r.model_type in SUPPORTED_METER_LOCATOR_MODEL_TYPES),
            None,
        )
    record_ids = (
        region_record.id if region_record else None,
        meter_record.id if meter_record else None,
    )
    if _cached_pipeline is not None and record_ids == _cached_ids:
        return _cached_pipeline
    if region_record is None and meter_record is None:
        _cached_ids = record_ids
        _cached_pipeline = MeterReadingPipeline()
        return _cached_pipeline
    region_path = _verified_path(region_record)
    meter_path = _verified_path(meter_record)
    versions = "+".join(
        record.version for record in (region_record, meter_record) if record is not None
    )
    pipeline = MeterReadingPipeline(
        f"modern-sequence-{versions}",
        region_model_path=region_path,
        meter_model_path=meter_path,
    )
    _cached_pipeline = pipeline
    _cached_ids = record_ids
    return _cached_pipeline
