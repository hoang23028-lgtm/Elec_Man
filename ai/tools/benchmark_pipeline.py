"""Measure pipeline latency on saved labels without modifying application data."""

import argparse
import json
from time import perf_counter

import numpy as np
from sqlalchemy import select

from ai.model_runtime import current_pipeline
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("limit must be between 1 and 100")
    root = get_settings().storage_root.resolve()
    with SessionLocal() as db:
        rows = db.execute(
            select(
                ImageRecord.relative_path,
                ImageRecord.sha256,
                MeterReading.final_meter_reading,
            )
            .join(MeterReading, MeterReading.image_id == ImageRecord.id)
            .where(MeterReading.review_status.in_(("LABELED", "CONFIRMED")))
            .order_by(ImageRecord.sha256)
        ).all()
    samples, seen = [], set()
    for path, digest, expected in rows:
        resolved = (root / path).resolve()
        if digest not in seen and resolved.is_relative_to(root) and resolved.is_file():
            samples.append((resolved, digest, expected))
            seen.add(digest)
        if len(samples) == args.limit:
            break
    if not samples:
        parser.error("No labeled images available")
    pipeline = current_pipeline()
    latencies, exact, attempts, hashes = [], 0, [], []
    # No labels, wheel counts or manual polygons are supplied to recognition.
    # First invocation includes cold OCR initialization; retain it in statistics.
    for index, (path, digest, expected) in enumerate(samples):
        started = perf_counter()
        result = pipeline.process(path)
        latencies.append(round((perf_counter() - started) * 1000, 2))
        exact += result.get("meter_reading_ai") == expected
        attempts.append(result.get("reader_diagnostics", {}).get("fallback_attempts"))
        hashes.append(digest)
        print(f"Processed {index + 1}/{len(samples)} in {latencies[-1]} ms", flush=True)
    print(
        json.dumps(
            {
                "scope": "saved_labels_diagnostic_not_holdout_cold_first_sample",
                "model_version": pipeline.model_version,
                "sample_hashes": hashes,
                "latencies_ms": latencies,
                "p50_ms": float(np.percentile(latencies, 50)),
                "p95_ms": float(np.percentile(latencies, 95)),
                "exact_readings": exact,
                "samples": len(samples),
                "fallback_attempts": attempts,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
