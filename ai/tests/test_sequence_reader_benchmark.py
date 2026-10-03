import pytest

from ai.readers.sequence import normalize_prediction
from ai.tools.benchmark_sequence_readers import summarize


@pytest.mark.parametrize(
    ("raw", "digits", "expected"),
    [
        ("063751", 5, "06375"),
        ("06375.1", 5, "06375"),
        (" 06375 ", 5, "06375"),
        ("GLEA63751", 5, "63751"),
        ("O6375", 5, None),
        ("12345678", 5, None),
    ],
)
def test_normalize_prediction_never_guesses_characters(raw, digits, expected):
    assert normalize_prediction(raw, digits) == expected


def test_summary_reports_abstention_separately_from_wrong_answer():
    rows = [
        {"expected": "12345", "predicted": "12345", "exact": True, "elapsed_ms": 10},
        {"expected": "67890", "predicted": None, "exact": False, "elapsed_ms": 20},
    ]
    result = summarize(rows)
    assert result["exact_accuracy"] == 0.5
    assert result["coverage"] == 0.5
    assert result["precision_when_answered"] == 1.0
