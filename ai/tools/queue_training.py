"""Queue human-labeled data for training without activating the output model."""

import argparse
import json
import re
from hashlib import sha256

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.schemas.result import ReadingPolygon
from app.services.dataset_policy import make_manifest
from app.services.dataset_service import dataset_samples
from app.services.training_service import (
    dataset_summary,
    eligible_clause,
    enqueue_training,
)
from sqlalchemy import select

from ai.pipeline.preprocessing import load_prepared_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experimental",
        action="store_true",
        help="One manual run below the configured threshold; leaves settings unchanged",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate images and saved labels without creating a run",
    )
    args = parser.parse_args()
    root = get_settings().storage_root.resolve()
    with SessionLocal() as db:
        rows = db.execute(
            select(ImageRecord, MeterReading)
            .join(MeterReading, MeterReading.image_id == ImageRecord.id)
            .where(*eligible_clause())
            .order_by(ImageRecord.sha256)
        ).all()
        rows = list(
            {image.sha256: (image, reading) for image, reading in rows}.values()
        )
        for image, reading in rows:
            path = (root / image.relative_path).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                parser.error(f"Ảnh không khả dụng: {image.id}")
            if sha256(path.read_bytes()).hexdigest() != image.sha256:
                parser.error(f"Checksum ảnh không khớp: {image.id}")
            if not re.fullmatch(r"[0-9]{4,8}", reading.final_meter_reading or ""):
                parser.error(f"Chỉ số không hợp lệ: {image.id}")
            ReadingPolygon.model_validate(reading.reading_polygon_json)
            ReadingPolygon.model_validate(reading.meter_polygon_json)
            if load_prepared_image(path) is None:
                parser.error(f"Không giải mã được ảnh: {image.id}")
        manifest = make_manifest(dataset_samples(db), experimental=args.experimental)
        summary = dataset_summary(db)
        print(
            json.dumps(
                {
                    "samples": len(rows),
                    "training_images": len(manifest["partitions"]["TRAIN"]),
                    "validation_images": len(manifest["partitions"]["VALIDATION"]),
                    "holdout_images": len(manifest["partitions"]["HOLDOUT"]),
                    "configured_minimum": summary.minimum_samples,
                    "experimental": args.experimental,
                    "note": "Use verified partitions. Experimental unknown identity splits never unlock activation.",
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if not args.check_only:
            run = enqueue_training(db, "MANUAL", None, experimental=args.experimental)
            print(
                json.dumps(
                    {"id": str(run.id), "status": run.status}, ensure_ascii=False
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
