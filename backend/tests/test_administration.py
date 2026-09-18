import pytest
from fastapi import HTTPException

from app.services.evaluation_service import _digit_counts
from app.services.settings_service import _audit_target, _validated_value


def test_digit_accuracy_counts_missing_and_wrong_digits() -> None:
    assert _digit_counts("63751.3", "63751.3") == (6, 6)
    assert _digit_counts("63751", "63751.3") == (5, 6)
    assert _digit_counts("63741.3", "63751.3") == (5, 6)


def test_setting_validation_coerces_numeric_values() -> None:
    assert _validated_value("confidence_ok_threshold", 0.9) == 0.9
    assert _validated_value("max_retry_count", 4.0) == 4


def test_setting_validation_rejects_unknown_or_out_of_range_values() -> None:
    with pytest.raises(HTTPException):
        _validated_value("unknown", 1)
    with pytest.raises(HTTPException):
        _validated_value("confidence_ok_threshold", 1.5)


def test_setting_audit_target_stays_within_database_limit() -> None:
    assert _audit_target(["max_retry_count"]) == "max_retry_count"
    target = _audit_target(
        [
            "confidence_ok_threshold",
            "confidence_review_threshold",
            "data_retention_days",
            "max_retry_count",
            "max_upload_size_mb",
            "worker_poll_interval_seconds",
        ]
    )
    assert target == "bulk:6 settings"
    assert len(target) <= 64
