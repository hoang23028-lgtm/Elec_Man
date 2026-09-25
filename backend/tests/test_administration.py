import pytest
from fastapi import HTTPException

from app.models.model_registry import ModelRecord
from app.services.evaluation_service import _digit_counts
from app.services.model_registry_service import _validate_activation_metrics
from app.services.settings_service import _audit_target, _validated_value


def test_digit_accuracy_counts_missing_and_wrong_digits() -> None:
    assert _digit_counts("63751.3", "63751.3") == (5, 5)
    assert _digit_counts("63751", "63751.3") == (5, 5)
    assert _digit_counts("63741.3", "63751.3") == (4, 5)


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


def test_trained_model_activation_requires_full_coverage_and_accuracy() -> None:
    record = ModelRecord(
        model_name="digits",
        model_type="meter_digit_centroid",
        version="test",
        file_path="test/model.npz",
        sha256="0" * 64,
        status="TESTING",
        metrics_json={"digit_coverage": 0.9, "validation_digit_accuracy": 0.95},
    )
    with pytest.raises(HTTPException) as error:
        _validate_activation_metrics(record)
    assert error.value.status_code == 422

    record.metrics_json = {"digit_coverage": 1.0, "validation_digit_accuracy": 0.9}
    _validate_activation_metrics(record)

    record.model_type = "meter_digit_hog_softmax"
    _validate_activation_metrics(record)
