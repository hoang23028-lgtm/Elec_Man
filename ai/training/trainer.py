from datetime import UTC, datetime
from hashlib import sha256

import numpy as np
from sqlalchemy import select

from ai.pipeline.preprocessing import load_prepared_image
from ai.pipeline.geometry import perspective_crop
from ai.pipeline.register import integer_register_strip
from ai.readers.consensus import ConsensusMeterReader
from ai.training.dataset import export_sequence_dataset, split_by_meter
from ai.training.keypoint_regressor import (
    KeypointRegionRegressor,
    extract_region_features,
)
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.models.model_registry import ModelRecord
from app.models.training_run import TrainingRun
from app.services.training_service import eligible_clause


def _reading_bbox(reading: MeterReading) -> tuple[float, float, float, float]:
    return (
        float(reading.reading_bbox_x),
        float(reading.reading_bbox_y),
        float(reading.reading_bbox_width),
        float(reading.reading_bbox_height),
    )


def _reading_polygon(reading: MeterReading) -> tuple[tuple[float, float], ...] | None:
    payload = reading.reading_polygon_json or {}
    points = payload.get("points")
    if not isinstance(points, list) or len(points) != 4:
        return None
    try:
        return tuple((float(point["x"]), float(point["y"])) for point in points)
    except (KeyError, TypeError, ValueError):
        return None


def _region_target(reading: MeterReading) -> np.ndarray:
    polygon = _reading_polygon(reading)
    if polygon is None:
        x, y, width, height = _reading_bbox(reading)
        polygon = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
    return np.asarray(polygon, dtype=np.float32)


def _meter_target(reading: MeterReading) -> np.ndarray:
    payload = reading.meter_polygon_json or {}
    points = payload.get("points")
    if not isinstance(points, list) or len(points) != 4:
        raise ValueError("Nhãn vùng toàn bộ công tơ không hợp lệ.")
    try:
        return np.asarray(
            [(float(point["x"]), float(point["y"])) for point in points],
            dtype=np.float32,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Nhãn vùng toàn bộ công tơ không hợp lệ.") from exc


def _set_stage(run_id, stage: str, progress: int) -> None:
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        if run is not None:
            run.stage = stage
            run.progress = progress
            db.add(
                AuditLog(
                    user_id=None,
                    action="TRAINING_STAGE_CHANGED",
                    target_type="training_run",
                    target_id=str(run.id),
                    details_json={"stage": stage, "progress": progress},
                    ip_address=None,
                )
            )
            db.commit()


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_character in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def _benchmark_sequence_reader(rows, storage_root) -> dict:
    reader = ConsensusMeterReader()
    answered = exact = character_errors = character_count = 0
    evaluated = 0
    unavailable = False
    try:
        for image, reading in rows:
            expected = str(reading.final_meter_reading or "")
            source = load_prepared_image(storage_root / image.relative_path)
            polygon = _reading_polygon(reading)
            if source is None or polygon is None:
                continue
            crop = integer_register_strip(perspective_crop(source, polygon))
            diagnostics: dict = {}
            predicted, _ = reader.read(
                crop, diagnostics=diagnostics, integer_digits=len(expected)
            )
            if diagnostics.get("decision") == "reader_service_unavailable":
                unavailable = True
                break
            evaluated += 1
            answered += predicted is not None
            exact += predicted == expected
            character_errors += _edit_distance(expected, predicted or "")
            character_count += len(expected)
    finally:
        reader.close()
    return {
        "sequence_reader_evaluated": not unavailable and evaluated > 0,
        "sequence_validation_samples": evaluated,
        "validation_reading_exact_accuracy": (
            round(exact / evaluated, 4) if evaluated else None
        ),
        "sequence_reader_coverage": round(answered / evaluated, 4)
        if evaluated
        else None,
        "sequence_character_error_rate": (
            round(character_errors / character_count, 4) if character_count else None
        ),
        "sequence_reader_unavailable": unavailable,
    }


def train_run(run_id) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        if run is None:
            raise ValueError("Không tìm thấy phiên huấn luyện.")
        run_metadata = dict(run.metrics_json or {})
        rows = db.execute(
            select(ImageRecord, MeterReading)
            .join(MeterReading, MeterReading.image_id == ImageRecord.id)
            .where(*eligible_clause())
            .order_by(ImageRecord.sha256)
        ).all()
    rows = list({image.sha256: (image, reading) for image, reading in rows}.values())
    if len(rows) < 2:
        raise ValueError("Không đủ mẫu hợp lệ để huấn luyện.")
    dataset_hash = sha256(
        "".join(
            f"{image.sha256}:{reading.final_meter_reading}:"
            f"{_reading_polygon(reading) or _reading_bbox(reading)}:{reading.meter_polygon_json}"
            for image, reading in rows
        ).encode()
    ).hexdigest()
    training_rows, validation_rows = split_by_meter(rows)
    version = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{str(run_id)[:8]}"

    _set_stage(run_id, "EXTRACTING_FEATURES", 25)
    region_training_features: list[np.ndarray] = []
    region_training_targets: list[np.ndarray] = []
    meter_training_targets: list[np.ndarray] = []
    for image, reading in training_rows:
        path = settings.storage_root / image.relative_path
        source = load_prepared_image(path)
        if source is not None:
            region_training_features.append(extract_region_features(source))
            region_training_targets.append(_region_target(reading))
            meter_training_targets.append(_meter_target(reading))
    if len(region_training_features) < 2:
        raise ValueError("Không đủ ảnh hợp lệ để huấn luyện các tầng định vị.")
    _set_stage(run_id, "VALIDATING", 65)
    region_model = KeypointRegionRegressor.train(
        region_training_features,
        region_training_targets,
    )
    meter_model = KeypointRegionRegressor.train(
        region_training_features,
        meter_training_targets,
    )
    region_errors: list[float] = []
    meter_errors: list[float] = []
    for image, reading in validation_rows:
        source = load_prepared_image(settings.storage_root / image.relative_path)
        prediction = region_model.predict(source) if source is not None else None
        meter_prediction = meter_model.predict(source) if source is not None else None
        if prediction is None:
            region_errors.append(1.0)
        else:
            predicted_polygon, _ = prediction
            region_errors.append(
                float(
                    np.mean(
                        np.abs(np.asarray(predicted_polygon) - _region_target(reading))
                    )
                )
            )
        if meter_prediction is None:
            meter_errors.append(1.0)
        else:
            predicted_meter_polygon, _ = meter_prediction
            meter_errors.append(
                float(
                    np.mean(
                        np.abs(
                            np.asarray(predicted_meter_polygon) - _meter_target(reading)
                        )
                    )
                )
            )
    region_error = float(np.mean(region_errors)) if region_errors else 1.0
    meter_error = float(np.mean(meter_errors)) if meter_errors else 1.0
    region_model = region_model.with_validation_error(region_error)
    meter_model = meter_model.with_validation_error(meter_error)
    _set_stage(run_id, "BUILDING_SEQUENCE_DATASET", 75)
    sequence_dataset_root = settings.models_root / "sequence_datasets" / version
    sequence_dataset = export_sequence_dataset(
        training_rows,
        validation_rows,
        settings.storage_root,
        sequence_dataset_root,
    )
    _set_stage(run_id, "BENCHMARKING_SEQUENCE_READER", 82)
    sequence_metrics = _benchmark_sequence_reader(
        validation_rows, settings.storage_root
    )
    region_relative_path = f"reading_region_ridge/{version}/model.npz"
    region_target = settings.models_root / region_relative_path
    region_target.parent.mkdir(parents=True, exist_ok=True)
    region_model.save(region_target)
    region_digest = sha256(region_target.read_bytes()).hexdigest()
    meter_relative_path = f"meter_locator_ridge/{version}/model.npz"
    meter_target = settings.models_root / meter_relative_path
    meter_target.parent.mkdir(parents=True, exist_ok=True)
    meter_model.save(meter_target)
    meter_digest = sha256(meter_target.read_bytes()).hexdigest()
    metrics = {
        **run_metadata,
        "validation_scope": "ground_truth_crop_and_digit_count",
        "end_to_end_evaluated": False,
        "preprocessing_version": "baseline-v1",
        "validation_split": "customer_group_or_image_hash_when_unknown",
        "sequence_reader": "ppocr-v6-small-parseq-tiny-consensus-v1",
        "sequence_reader_trainable": False,
        "sequence_dataset": sequence_dataset,
        **sequence_metrics,
        "validation_region_mean_error": round(region_error, 4),
        "validation_region_accuracy": round(max(0.0, 1.0 - region_error * 4.0), 4),
        "validation_meter_region_mean_error": round(meter_error, 4),
        "validation_meter_region_accuracy": round(max(0.0, 1.0 - meter_error * 4.0), 4),
        "training_images": len(training_rows),
        "validation_images": len(validation_rows),
        "algorithm": "two-stage-region-ridge-modern-sequence-consensus-v1",
    }
    _set_stage(run_id, "REGISTERING_MODEL", 90)
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        region_record = ModelRecord(
            model_name="reading-region-specialized",
            model_type="reading_region_ridge",
            version=version,
            file_path=region_relative_path,
            metrics_json=metrics,
            status="TESTING",
            sha256=region_digest,
            created_at=datetime.now(UTC),
        )
        meter_record = ModelRecord(
            model_name="meter-locator-specialized",
            model_type="meter_locator_ridge",
            version=version,
            file_path=meter_relative_path,
            metrics_json=metrics,
            status="TESTING",
            sha256=meter_digest,
            created_at=datetime.now(UTC),
        )
        db.add_all((region_record, meter_record))
        db.flush()
        run.status = "COMPLETED"
        run.stage = "COMPLETED"
        run.progress = 100
        run.sample_count = len(rows)
        run.training_count = len(training_rows)
        run.validation_count = len(validation_rows)
        run.dataset_hash = dataset_hash
        run.metrics_json = metrics
        run.model_id = region_record.id
        run.completed_at = datetime.now(UTC)
        db.add(
            AuditLog(
                user_id=None,
                action="TRAINING_COMPLETED",
                target_type="training_run",
                target_id=str(run.id),
                details_json={
                    "dataset_hash": dataset_hash,
                    "sample_count": len(rows),
                    "training_count": len(training_rows),
                    "validation_count": len(validation_rows),
                    "model_id": str(region_record.id),
                    "region_model_id": str(region_record.id),
                    "meter_model_id": str(meter_record.id),
                    "model_version": version,
                    "region_model_sha256": region_digest,
                    "meter_model_sha256": meter_digest,
                    "metrics": metrics,
                },
                ip_address=None,
            )
        )
        db.commit()
