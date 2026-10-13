"""Read-only paired diagnostic: automatic pipeline vs human-crop sequence reader.

All previously labeled images are development data, never an independent test.
No labels, inference rows, training runs or model records are written.
"""

import argparse
import json
import re
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import numpy as np
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from sqlalchemy import select, text

from ai.model_runtime import current_pipeline
from ai.pipeline.geometry import perspective_crop
from ai.pipeline.preprocessing import load_prepared_image
from ai.readers.consensus import ConsensusMeterReader


def summary(rows, field):
    answers = sum(row[field]["predicted"] is not None for row in rows)
    exact = sum(row[field]["predicted"] == row["expected"] for row in rows)
    latencies = [row[field]["elapsed_ms"] for row in rows]
    return {
        "samples": len(rows),
        "answered": answers,
        "exact": exact,
        "wrong_answers": answers - exact,
        "exact_accuracy": exact / len(rows) if rows else None,
        "coverage": answers / len(rows) if rows else None,
        "precision_when_answered": exact / answers if answers else None,
        "p50_ms": float(np.percentile(latencies, 50)) if rows else None,
        "p95_ms": float(np.percentile(latencies, 95)) if rows else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output file; reports are not overwritten")
    root = get_settings().storage_root.resolve()
    with SessionLocal() as db:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SET TRANSACTION READ ONLY"))
        records = db.execute(
            select(ImageRecord, MeterReading)
            .join(
                MeterReading,
                MeterReading.image_id == ImageRecord.id,
            )
            .where(
                MeterReading.review_status.in_(("LABELED", "CONFIRMED")),
                MeterReading.reviewed_by.is_not(None),
                MeterReading.reading_polygon_json.is_not(None),
            )
            .order_by(ImageRecord.sha256)
        ).all()
    pipeline = current_pipeline()
    reader = ConsensusMeterReader()
    rows, seen, invalid = [], set(), 0
    try:
        for image, reading in records:
            path = (root / image.relative_path).resolve()
            expected = reading.final_meter_reading or ""
            points = (reading.reading_polygon_json or {}).get("points", [])
            if (
                image.sha256 in seen
                or not re.fullmatch(r"[0-9]{4,8}", expected)
                or not path.is_relative_to(root)
                or not path.is_file()
                or len(points) != 4
                or sha256(path.read_bytes()).hexdigest() != image.sha256
            ):
                invalid += 1
                continue
            seen.add(image.sha256)
            started = perf_counter()
            result = pipeline.process(path)  # No ground-truth geometry/digit count.
            automatic = {
                "predicted": result.get("meter_reading_ai"),
                "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                "reading_bbox": (result.get("regions") or {}).get("reading"),
            }
            prepared = load_prepared_image(path)
            polygon = tuple((float(point["x"]), float(point["y"])) for point in points)
            crop = perspective_crop(prepared, polygon)
            started = perf_counter()
            diagnostics = {}
            predicted, _ = reader.read(
                crop, diagnostics=diagnostics, integer_digits=len(expected)
            )
            rows.append(
                {
                    "sha256": image.sha256,
                    "expected": expected,
                    "known_meter_identity": bool(
                        reading.matched_customer_id or reading.final_customer_id
                    ),
                    "automatic": automatic,
                    "human_crop": {
                        "predicted": predicted,
                        "elapsed_ms": round((perf_counter() - started) * 1000, 2),
                        "decision": diagnostics.get("decision"),
                    },
                }
            )
            print(f"Đã đánh giá {len(rows)}/{len(records)} ảnh", flush=True)
    finally:
        reader.close()
        pipeline.meter_reader.close()
    report = {
        "scope": "all_existing_labels_development_diagnostic_cold_first_sample",
        "independent_holdout": False,
        "database_mutated": False,
        "model_version": pipeline.model_version,
        "has_meter_model": pipeline.has_meter_model,
        "has_region_model": pipeline.has_region_model,
        "invalid_or_duplicate_samples": invalid,
        "unknown_meter_identity_samples": sum(
            not row["known_meter_identity"] for row in rows
        ),
        "automatic": summary(rows, "automatic"),
        "human_crop": summary(rows, "human_crop"),
        "results": rows,
        "note": "Human crop uses known geometry/digit count; automatic does not. Neither is independent holdout.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "results"},
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
