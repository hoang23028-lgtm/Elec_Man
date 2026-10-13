import numpy as np
import pytest

from ai.pipeline.geometry import transform_polygon
from ai.training.metrics import (
    edit_distance,
    polygon_iou,
    reading_metrics,
    wilson_upper,
)


def test_perspective_round_trip_and_iou():
    frame = ((0.1, 0.1), (0.9, 0.2), (0.85, 0.9), (0.15, 0.8))
    region = ((0.3, 0.4), (0.7, 0.4), (0.7, 0.5), (0.3, 0.5))
    mapped = transform_polygon(region, frame)
    recovered = transform_polygon(mapped, frame, inverse=True)
    assert np.allclose(region, recovered, atol=1e-6)
    assert polygon_iou(region, recovered) == pytest.approx(1, abs=1e-6)
    assert polygon_iou(region, ((0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1))) == 0
    assert polygon_iou(None, region) == 0


def test_exact_accuracy_abstention_and_high_confidence_wrong_reading():
    records = [
        {
            "expected": "00120",
            "predicted": "00120",
            "confidence": 0.99,
            "elapsed_ms": 10,
        },
        {
            "expected": "00121",
            "predicted": "00120",
            "confidence": 0.99,
            "elapsed_ms": 20,
        },
        {"expected": "00122", "predicted": None, "confidence": 0, "elapsed_ms": 30},
    ]
    result = reading_metrics(records)
    assert result["exact_accuracy"] == 1 / 3
    assert result["coverage"] == 2 / 3
    assert result["wrong_answers"] == 1
    assert result["high_confidence_errors"] == 1
    assert result["character_error_rate"] == 6 / 15
    assert result["score_calibrated"] is False
    assert result["p95_ms"] == 29
    assert edit_distance("00120", "0120") == 1


def test_no_samples_never_claim_accuracy_or_zero_error_bound():
    result = reading_metrics([])
    assert result["exact_accuracy"] is None
    assert result["p95_ms"] is None
    assert wilson_upper(0, 0) is None
    assert wilson_upper(0, 30) > 0.1
