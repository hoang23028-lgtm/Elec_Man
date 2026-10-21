"""Measure pipeline latency on saved labels without modifying application data."""

import argparse
import json
from hashlib import sha256
from pathlib import Path
from tempfile import gettempdir
from time import perf_counter

import numpy as np
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.services.training_service import eligible_clause
from sqlalchemy import select

from ai.model_runtime import current_pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--mode", choices=("automatic", "selected"), default="automatic"
    )
    parser.add_argument("--compare-encoder", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100 or not 2 <= args.repeats <= 10:
        parser.error("limit phải 1–100, repeats phải 2–10")
    root = get_settings().storage_root.resolve()
    if args.output and (
        args.output.suffix != ".json"
        or not any(
            args.output.resolve().is_relative_to(base)
            for base in (
                get_settings().models_root.resolve(),
                Path(gettempdir()).resolve(),
            )
        )
        or args.output.exists()
    ):
        parser.error("Report phải là JSON mới bên trong MODELS_ROOT hoặc thư mục tạm.")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        rows = db.execute(
            select(
                ImageRecord.relative_path,
                ImageRecord.sha256,
                MeterReading.final_meter_reading,
                MeterReading.reading_polygon_json,
            )
            .join(MeterReading, MeterReading.image_id == ImageRecord.id)
            .where(*eligible_clause())
            .order_by(ImageRecord.sha256)
        ).all()
    samples, seen = [], set()
    for path, digest, expected, polygon in rows:
        resolved = (root / path).resolve()
        if digest not in seen and resolved.is_relative_to(root) and resolved.is_file():
            if sha256(resolved.read_bytes()).hexdigest() != digest:
                raise ValueError("Checksum ảnh benchmark không khớp.")
            samples.append((resolved, digest, expected, polygon))
            seen.add(digest)
        if len(samples) == args.limit:
            break
    if not samples:
        parser.error("No labeled images available")
    pipeline = current_pipeline()
    modes = ["torch", "onnx"] if args.compare_encoder else ["torch"]
    results = {mode: [] for mode in modes}
    original = pipeline.meter_reader.parseq_model
    try:
        for repeat in range(args.repeats):
            for path, digest, expected, polygon in samples:
                for mode in modes if repeat % 2 == 0 else list(reversed(modes)):
                    pipeline.meter_reader.parseq_model = {
                        **(original or {}),
                        "encoder_runtime": mode,
                    }
                    started = perf_counter()
                    result = pipeline.process(
                        path,
                        reading_polygon=tuple(
                            (p["x"], p["y"]) for p in polygon["points"]
                        )
                        if args.mode == "selected"
                        else None,
                        integer_digits=len(expected)
                        if args.mode == "selected"
                        else None,
                    )
                    results[mode].append(
                        {
                            "repeat": repeat,
                            "sha256": digest,
                            "elapsed_ms": (perf_counter() - started) * 1000,
                            "predicted": result.get("meter_reading_ai"),
                            "exact": result.get("meter_reading_ai") == expected,
                            "timings_ms": result.get("timings_ms", {}),
                            "customer_found": result.get("customer_id_ai") is not None,
                            "customer_fallback_attempts": result.get(
                                "customer_ocr_diagnostics", {}
                            ).get("fallback_attempts", 0),
                            "customer_budget_exhausted": result.get(
                                "customer_ocr_diagnostics", {}
                            ).get("fallback_budget_exhausted", False),
                            "readers": result.get("reader_diagnostics", {}),
                            "service_unavailable": result.get(
                                "reader_diagnostics", {}
                            ).get("decision")
                            == "reader_service_unavailable",
                        }
                    )
            print(
                f"Đã đo vòng {repeat + 1}/{args.repeats}, {len(samples)} ảnh",
                flush=True,
            )
    finally:
        pipeline.meter_reader.parseq_model = original
        pipeline.meter_reader.close()
    summary = {}
    for mode, records in results.items():
        warm = [r for r in records if r["repeat"] > 0]
        values = [r["elapsed_ms"] for r in warm]
        keys = {key for r in warm for key in r["timings_ms"]}
        summary[mode] = {
            "samples": len(warm),
            "exact": sum(r["exact"] for r in warm),
            "service_errors": sum(r["service_unavailable"] for r in records),
            "customer_found_calls": sum(r["customer_found"] for r in warm),
            "customer_budget_exhausted_calls": sum(
                r["customer_budget_exhausted"] for r in warm
            ),
            "customer_accuracy_evaluated": False,
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "stages": {
                key: {
                    "p50_ms": float(
                        np.percentile(
                            [
                                r["timings_ms"][key]
                                for r in warm
                                if key in r["timings_ms"]
                            ],
                            50,
                        )
                    ),
                    "p95_ms": float(
                        np.percentile(
                            [
                                r["timings_ms"][key]
                                for r in warm
                                if key in r["timings_ms"]
                            ],
                            95,
                        )
                    ),
                }
                for key in keys
            },
        }
    parity = (
        all(
            a["predicted"] == b["predicted"]
            and not a["service_unavailable"]
            and not b["service_unavailable"]
            for a, b in zip(results["torch"], results.get("onnx", []), strict=True)
        )
        if args.compare_encoder
        else None
    )
    report = {
        "scope": "saved_labels_diagnostic_not_independent_holdout",
        "mode": args.mode,
        "manual_crop_and_known_digits": args.mode == "selected",
        "cold_repeat_excluded_from_warm_summary": True,
        "model_version": pipeline.model_version,
        "sample_hashes": [s[1] for s in samples],
        "summary": summary,
        "torch_onnx_value_parity": parity,
        "results": results,
        "database_mutated": False,
    }
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "results"}, indent=2
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
