import pytest
from fastapi import HTTPException

from app.models.model_registry import ModelRecord
from app.services.model_registry_service import _validate_activation_metrics


def candidate(**metrics):
    return ModelRecord(
        model_type="reading_region_ridge",
        metrics_json={
            "validation_region_accuracy": 0.9,
            "validation_groups_verified": True,
            "validation_images": 30,
            **metrics,
        },
    )


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1, 1.5, True, "0.99", None])
def test_non_numeric_or_invalid_scores_cannot_activate_a_model(score):
    with pytest.raises(HTTPException):
        _validate_activation_metrics(candidate(validation_region_accuracy=score))


@pytest.mark.parametrize(
    "metadata",
    [
        {"validation_groups_verified": False},
        {"validation_groups_verified": None},
        {"validation_images": 7},
        {"validation_images": True},
        {"validation_images": "200"},
    ],
)
def test_diagnostic_or_too_small_validation_does_not_unlock_activation(metadata):
    with pytest.raises(HTTPException):
        _validate_activation_metrics(candidate(**metadata))


def test_verified_group_split_and_finite_score_allow_manual_activation():
    _validate_activation_metrics(candidate())
