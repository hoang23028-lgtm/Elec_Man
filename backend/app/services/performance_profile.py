"""Aggregate only known finite timings, never return raw OCR/customer fields."""

from math import isfinite

STAGES = {
    "decode",
    "preprocess",
    "quality",
    "meter_location",
    "reading_region",
    "scene_ocr",
    "customer_ocr",
    "crop",
    "read_digits",
    "validation",
    "crop_and_quality",
}


def summarize_timings(rows):
    groups = {"automatic": {}, "manual": {}}
    for timings, manual, candidates in rows:
        group = groups["manual" if manual is True else "automatic"]
        entries = dict(timings) if isinstance(timings, dict) else {}
        if isinstance(candidates, dict):
            for backend in ("ppocr", "parseq"):
                result = candidates.get(backend)
                if isinstance(result, dict):
                    entries[f"{backend}_rpc"] = result.get("rpc_ms")
        for key, value in entries.items():
            if (
                key in STAGES | {"ppocr_rpc", "parseq_rpc"}
                and not isinstance(value, bool)
                and isinstance(value, int | float)
                and isfinite(value)
                and 0 <= value <= 86400000
            ):
                group.setdefault(key, []).append(float(value))
    return {
        name: {
            key: {
                "samples": len(values),
                "p50_ms": round(sorted(values)[int((len(values) - 1) * 0.5)], 2),
                "p95_ms": round(sorted(values)[int((len(values) - 1) * 0.95)], 2),
            }
            for key, values in group.items()
        }
        for name, group in groups.items()
    }
