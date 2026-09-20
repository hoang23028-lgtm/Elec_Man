from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256

import numpy as np
from sqlalchemy import select

from ai.training.digit_model import sample_features
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.models.model_registry import ModelRecord
from app.models.training_run import TrainingRun
from app.services.training_service import eligible_clause


def _set_stage(run_id, stage: str, progress: int) -> None:
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        if run is not None:
            run.stage = stage
            run.progress = progress
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
            f"{image.sha256}:{reading.final_meter_reading}" for image, reading in rows
        ).encode()
    ).hexdigest()
    validation_rows = [row for row in rows if int(row[0].sha256[:2], 16) % 5 == 0]
    if not validation_rows:
        validation_rows = [rows[-1]]
    validation_ids = {image.id for image, _ in validation_rows}
    training_rows = [row for row in rows if row[0].id not in validation_ids]
    if not training_rows:
        training_rows, validation_rows = rows[:-1], rows[-1:]

    _set_stage(run_id, "EXTRACTING_FEATURES", 25)
    grouped: dict[int, list[np.ndarray]] = defaultdict(list)
    for image, reading in training_rows:
        path = settings.storage_root / image.relative_path
        for label, feature in sample_features(path, reading.final_meter_reading or ""):
            grouped[label].append(feature)
    if len(grouped) < 2:
        raise ValueError("Dữ liệu chưa tạo được đặc trưng cho ít nhất hai chữ số.")

    labels = np.array(sorted(grouped), dtype=np.int64)
    centroids = np.stack(
        [np.mean(grouped[int(label)], axis=0) for label in labels]
    ).astype(np.float32)
    _set_stage(run_id, "VALIDATING", 65)
    correct = total = 0
    for image, reading in validation_rows:
        for expected, feature in sample_features(
            settings.storage_root / image.relative_path,
            reading.final_meter_reading or "",
        ):
            distances = np.mean((centroids - feature) ** 2, axis=1)
            predicted = int(labels[int(np.argmin(distances))])
            correct += int(predicted == expected)
            total += 1

    version = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{str(run_id)[:8]}"
    relative_path = f"meter_digit_centroid/{version}/model.npz"
    target = settings.models_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(target, labels=labels, centroids=centroids)
    digest = sha256(target.read_bytes()).hexdigest()
    metrics = {
        "validation_digit_accuracy": round(correct / total, 4) if total else None,
        "validation_digits": total,
        "digit_classes": labels.tolist(),
        "digit_coverage": round(len(labels) / 10, 4),
        "training_images": len(training_rows),
        "validation_images": len(validation_rows),
        "algorithm": "normalized-pixel-nearest-centroid-v1",
    }
    _set_stage(run_id, "REGISTERING_MODEL", 90)
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        model = ModelRecord(
            model_name="meter-digit-centroid",
            model_type="meter_digit_centroid",
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
        db.commit()
