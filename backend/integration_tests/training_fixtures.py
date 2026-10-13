"""Synthetic metadata only, in the disposable integration database."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select

from app.models.ai_result import AiResult
from app.models.batch import Batch
from app.models.dataset_annotation import DatasetAnnotation
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.models.user import User

POLYGON = {
    "points": [{"x": x, "y": y} for x, y in ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9))]
}


def samples(db, count=1, partition="UNASSIGNED"):
    actor = db.scalar(select(User).where(User.username == "super_admin"))
    batch = Batch(original_folder_name="synthetic-training-policy", batch_code=f"SYN-{uuid4().hex}")
    db.add(batch)
    db.flush()
    images = []
    for index in range(count):
        token = uuid4().hex
        image = ImageRecord(
            batch_id=batch.id,
            original_filename=f"synthetic-{token}.png",
            stored_filename=f"{token}.png",
            relative_path=f"synthetic/{token}.png",
            thumbnail_path=f"synthetic/{token}.thumb.png",
            file_size=10,
            mime_type="image/png",
            sha256=sha256(token.encode()).hexdigest(),
            width=640,
            height=480,
            status="REVIEW_REQUIRED",
        )
        db.add(image)
        db.flush()
        ai = AiResult(
            image_id=image.id,
            model_version="synthetic-policy",
            customer_confidence=0,
            meter_confidence=0,
            detection_confidence=0,
            image_quality_score=0,
            final_confidence=0,
            status="REVIEW_REQUIRED",
            processing_time_ms=1,
            raw_result_json={},
        )
        db.add(ai)
        db.flush()
        reading = MeterReading(
            image_id=image.id,
            ai_result_id=ai.id,
            review_status="LABELED",
            final_meter_reading="00120",
            reviewed_by=actor.id,
            reading_polygon_json=POLYGON,
            meter_polygon_json=POLYGON,
            bbox_reviewed_by=actor.id,
            meter_bbox_reviewed_by=actor.id,
        )
        db.add(reading)
        db.flush()
        if partition != "UNASSIGNED":
            db.add(
                DatasetAnnotation(
                    image_id=image.id,
                    group_key=f"SYN-{token}",
                    partition=partition,
                    identity_verified=True,
                    label_verified=True,
                    label_revision=reading.revision,
                    updated_by=actor.id,
                    holdout_locked_at=datetime.now(UTC) if partition == "HOLDOUT" else None,
                )
            )
        images.append(image.id)
    db.commit()
    return images
