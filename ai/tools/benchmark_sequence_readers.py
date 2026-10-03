"""Benchmark sequence readers on a deterministic, read-only label split."""

import argparse
import json
import platform
import re
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import numpy as np
from sqlalchemy import select

from ai.readers.sequence import (
    PaddleV6SmallReader,
    ParseqTinyReader,
    package_version,
)
from ai.pipeline.geometry import perspective_crop
from ai.pipeline.preprocessing import load_prepared_image
from ai.pipeline.register import integer_register_strip
from ai.training.dataset import split_by_meter
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.schemas.result import ReadingPolygon


def edit_distance(left: str, right: str) -> int:
    """Return Levenshtein distance without importing an optional OCR runtime."""
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


def load_validation_samples() -> list[dict]:
    storage_root = get_settings().storage_root.resolve()
    with SessionLocal() as db:
        rows = db.execute(
            select(ImageRecord, MeterReading)
            .join(MeterReading, MeterReading.image_id == ImageRecord.id)
            .where(
                MeterReading.review_status.in_(("LABELED", "CONFIRMED")),
                MeterReading.reviewed_by.is_not(None),
                MeterReading.bbox_reviewed_by.is_not(None),
            )
            .order_by(ImageRecord.sha256)
        ).all()
    unique_rows, seen = [], set()
    for image, reading in rows:
        expected = reading.final_meter_reading or ""
        path = (storage_root / image.relative_path).resolve()
        if (
            image.sha256 in seen
            or not re.fullmatch(r"[0-9]{4,8}", expected)
            or not reading.reading_polygon_json
            or not path.is_relative_to(storage_root)
            or not path.is_file()
            or sha256(path.read_bytes()).hexdigest() != image.sha256
        ):
            continue
        unique_rows.append((image, reading))
        seen.add(image.sha256)
    _, validation = split_by_meter(unique_rows)
    samples = []
    for image, reading in validation:
        polygon = ReadingPolygon.model_validate(reading.reading_polygon_json)
        samples.append(
            {
                "path": (storage_root / image.relative_path).resolve(),
                "sha256": image.sha256,
                "expected": reading.final_meter_reading,
                "integer_digits": len(reading.final_meter_reading),
                "polygon": tuple((point.x, point.y) for point in polygon.points),
            }
        )
    return samples


def summarize(rows: list[dict]) -> dict:
    latencies = [row["elapsed_ms"] for row in rows]
    answered = sum(row["predicted"] is not None for row in rows)
    exact = sum(row["exact"] for row in rows)
    characters = sum(len(row["expected"]) for row in rows)
    errors = sum(edit_distance(row["expected"], row["predicted"] or "") for row in rows)
    return {
        "samples": len(rows),
        "exact_matches": exact,
        "exact_accuracy": exact / len(rows),
        "coverage": answered / len(rows),
        "precision_when_answered": exact / answered if answered else None,
        "character_error_rate": errors / characters if characters else None,
        "p50_ms": float(np.percentile(latencies, 50)),
        "p95_ms": float(np.percentile(latencies, 95)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reader", choices=("ppocr-v6-small", "parseq-tiny"), required=True
    )
    parser.add_argument("--parseq-repository", type=Path, default=Path("/opt/parseq"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output report already exists")
    samples = load_validation_samples()
    if not samples:
        parser.error("No deterministic validation samples are available")
    initialized = perf_counter()
    reader = (
        PaddleV6SmallReader()
        if args.reader == "ppocr-v6-small"
        else ParseqTinyReader(args.parseq_repository)
    )
    initialization_ms = round((perf_counter() - initialized) * 1000)
    rows = []
    for index, sample in enumerate(samples):
        prepared = load_prepared_image(sample["path"])
        if prepared is None:
            raise ValueError("A verified sample can no longer be decoded")
        crop = integer_register_strip(perspective_crop(prepared, sample["polygon"]))
        started = perf_counter()
        predicted, score = reader.predict(crop, sample["integer_digits"])
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        rows.append(
            {
                "sha256": sample["sha256"],
                "expected": sample["expected"],
                "predicted": predicted,
                "exact": predicted == sample["expected"],
                "score_uncalibrated": round(score, 6),
                "elapsed_ms": elapsed_ms,
            }
        )
        print(
            f"{reader.name}: {index + 1}/{len(samples)} ({elapsed_ms} ms)", flush=True
        )
    report = {
        "scope": "deterministic_validation_human_crop_known_integer_digit_count",
        "independent_holdout": False,
        "database_mutated": False,
        "reader": reader.name,
        "versions": (
            {
                "paddleocr": package_version("paddleocr"),
                "paddlepaddle": package_version("paddlepaddle"),
            }
            if args.reader == "ppocr-v6-small"
            else {"torch": package_version("torch"), "parseq_commit": "1902db043c02"}
        ),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "initialization_ms": initialization_ms,
        "summary": summarize(rows),
        "results": rows,
        "note": (
            "Diagnostic comparison only: labels were previously used by this project and "
            "meter identity is unavailable for most samples. Scores are not calibrated probabilities."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
