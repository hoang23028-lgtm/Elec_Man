from datetime import UTC, datetime
from hashlib import sha256

import numpy as np
import cv2
from sqlalchemy import select

from ai.training.digit_model import DigitHogSoftmaxModel, sample_features
from ai.training.region_model import ReadingRegionRegressor, region_features
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


def train_run(run_id) -> None:
    settings = get_settings()
    with SessionLocal() as db:
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
            f"{image.sha256}:{reading.final_meter_reading}:{_reading_polygon(reading) or _reading_bbox(reading)}"
            for image, reading in rows
        ).encode()
    ).hexdigest()
    validation_rows = [
        row
        for row in rows
        if int(
            sha256((row[1].final_customer_id or row[0].sha256).encode()).hexdigest()[
                :2
            ],
            16,
        )
        % 5
        == 0
    ]
    if not validation_rows:
        validation_rows = [rows[-1]]
    validation_ids = {image.id for image, _ in validation_rows}
    training_rows = [row for row in rows if row[0].id not in validation_ids]
    if not training_rows:
        training_rows, validation_rows = rows[:-1], rows[-1:]

    _set_stage(run_id, "EXTRACTING_FEATURES", 25)
    training_features: list[np.ndarray] = []
    training_targets: list[int] = []
    region_training_features: list[np.ndarray] = []
    region_training_targets: list[np.ndarray] = []
    reading_lengths: list[int] = []
    for image, reading in training_rows:
        path = settings.storage_root / image.relative_path
        source = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if source is not None:
            region_training_features.append(region_features(source))
            region_training_targets.append(_region_target(reading))
        digits = "".join(
            character
            for character in (reading.final_meter_reading or "")
            if character.isdigit()
        )
        if digits:
            reading_lengths.append(len(digits))
        for label, feature in sample_features(
            path,
            reading.final_meter_reading or "",
            augment=True,
            reading_bbox=_reading_bbox(reading),
            reading_polygon=_reading_polygon(reading),
        ):
            training_targets.append(label)
            training_features.append(feature)
    if len(set(training_targets)) < 2:
        raise ValueError("Dữ liệu chưa tạo được đặc trưng cho ít nhất hai chữ số.")

    model = DigitHogSoftmaxModel.train(
        training_features,
        training_targets,
        seed=int(dataset_hash[:8], 16),
    )
    _set_stage(run_id, "VALIDATING", 65)
    region_model = ReadingRegionRegressor.train(
        region_training_features,
        region_training_targets,
    )
    region_errors: list[float] = []
    for image, reading in validation_rows:
        source = cv2.imread(
            str(settings.storage_root / image.relative_path), cv2.IMREAD_COLOR
        )
        prediction = region_model.predict(source) if source is not None else None
        if prediction is None:
            region_errors.append(1.0)
            continue
        predicted_polygon, _ = prediction
        region_errors.append(
            float(
                np.mean(np.abs(np.asarray(predicted_polygon) - _region_target(reading)))
            )
        )
    region_error = float(np.mean(region_errors)) if region_errors else 1.0
    region_model = region_model.with_validation_error(region_error)
    model = model.with_training_metadata(reading_lengths, region_model)
    correct = total = 0
    exact_readings = evaluated_readings = 0
    for image, reading in validation_rows:
        validation_samples = sample_features(
            settings.storage_root / image.relative_path,
            reading.final_meter_reading or "",
            reading_bbox=_reading_bbox(reading),
            reading_polygon=_reading_polygon(reading),
        )
        if not validation_samples:
            continue
        expected = "".join(str(label) for label, _ in validation_samples)
        predicted, _ = model.predict_features(
            [feature for _, feature in validation_samples]
        )
        evaluated_readings += 1
        exact_readings += int(predicted == expected)
        correct += sum(
            left == right for left, right in zip(expected, predicted, strict=True)
        )
        total += len(expected)

    version = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{str(run_id)[:8]}"
    relative_path = f"meter_digit_hog_softmax/{version}/model.npz"
    target = settings.models_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    model.save(target)
    digest = sha256(target.read_bytes()).hexdigest()
    metrics = {
        "validation_digit_accuracy": round(correct / total, 4) if total else None,
        "validation_reading_exact_accuracy": (
            round(exact_readings / evaluated_readings, 4)
            if evaluated_readings
            else None
        ),
        "validation_region_mean_error": round(region_error, 4),
        "validation_region_accuracy": round(max(0.0, 1.0 - region_error * 4.0), 4),
        "validation_digits": total,
        "digit_classes": model.labels.tolist(),
        "digit_coverage": round(len(model.labels) / 10, 4),
        "training_digits": len(training_features),
        "training_images": len(training_rows),
        "validation_images": len(validation_rows),
        "algorithm": "region-ridge-hog-softmax-v2",
        "augmentation_factor": 10,
    }
    _set_stage(run_id, "REGISTERING_MODEL", 90)
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        model = ModelRecord(
            model_name="meter-digit-specialized",
            model_type="meter_digit_hog_softmax",
            version=version,
            file_path=relative_path,
            metrics_json=metrics,
            status="TESTING",
            sha256=digest,
            created_at=datetime.now(UTC),
        )
        db.add(model)
        db.flush()
        run.status = "COMPLETED"
        run.stage = "COMPLETED"
        run.progress = 100
        run.sample_count = len(rows)
        run.training_count = len(training_rows)
        run.validation_count = len(validation_rows)
        run.dataset_hash = dataset_hash
        run.metrics_json = metrics
        run.model_id = model.id
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
                    "model_id": str(model.id),
                    "model_version": version,
                    "model_sha256": digest,
                    "metrics": metrics,
                },
                ip_address=None,
            )
        )
        db.commit()
