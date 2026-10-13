from math import sqrt
from time import perf_counter

import cv2
import numpy as np


def edit_distance(left, right):
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        next_row = [i]
        for j, b in enumerate(right, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j - 1] + (a != b)))
        row = next_row
    return row[-1]


def polygon_iou(predicted, expected):
    a, b = np.asarray(predicted, np.float32), np.asarray(expected, np.float32)
    if (
        a.shape != (4, 2)
        or b.shape != (4, 2)
        or not np.all(np.isfinite(a))
        or not np.all(np.isfinite(b))
    ):
        return 0.0
    intersection, _ = cv2.intersectConvexConvex(a, b)
    union = abs(cv2.contourArea(a)) + abs(cv2.contourArea(b)) - intersection
    return max(0.0, min(1.0, float(intersection / union))) if union > 0 else 0.0


def wilson_upper(errors, count):
    if not count:
        return None
    z = 1.96
    p = errors / count
    return min(
        1.0,
        (
            p
            + z * z / (2 * count)
            + z * sqrt(p * (1 - p) / count + z * z / (4 * count * count))
        )
        / (1 + z * z / count),
    )


def reading_metrics(records):
    count = len(records)
    answered = [r for r in records if r.get("predicted") is not None]
    exact = sum(r.get("predicted") == r["expected"] for r in records)
    high = [r for r in answered if r.get("confidence", 0) >= 0.9]
    wrong_high = sum(r["predicted"] != r["expected"] for r in high)
    return {
        "samples": count,
        "exact_accuracy": exact / count if count else None,
        "coverage": len(answered) / count if count else None,
        "character_error_rate": sum(
            edit_distance(r["expected"], r.get("predicted") or "") for r in records
        )
        / max(1, sum(len(r["expected"]) for r in records)),
        "wrong_answers": len(answered) - exact,
        "high_confidence_samples": len(high),
        "high_confidence_errors": wrong_high,
        "high_confidence_error_upper_95": wilson_upper(wrong_high, len(high)),
        "score_calibrated": False,
        "p50_ms": float(np.percentile([r["elapsed_ms"] for r in records], 50))
        if count
        else None,
        "p95_ms": float(np.percentile([r["elapsed_ms"] for r in records], 95))
        if count
        else None,
    }


def evaluate_predictions(inputs, predict):
    records = []
    for item, expected in inputs:
        started = perf_counter()
        value, confidence = predict(item, len(expected))
        records.append(
            {
                "expected": expected,
                "predicted": value,
                "confidence": confidence,
                "elapsed_ms": (perf_counter() - started) * 1000,
            }
        )
    return reading_metrics(records)
