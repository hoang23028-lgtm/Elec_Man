from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.schemas.dataset import DatasetAnnotationRequest, TrainingStartRequest
from app.services.dataset_policy import make_manifest, sample_issues

POLYGON = {
    "points": [{"x": x, "y": y} for x, y in ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9))]
}


def sample(index, partition="TRAIN", group=None):
    return {
        "image": {"id": str(index), "sha256": f"{index:064x}"},
        "reading": {
            "revision": 3,
            "review_status": "LABELED",
            "reviewed_by": "actor",
            "bbox_reviewed_by": "actor",
            "meter_bbox_reviewed_by": "actor",
            "final_meter_reading": "00120",
            "reading_polygon_json": deepcopy(POLYGON),
            "meter_polygon_json": deepcopy(POLYGON),
        },
        "annotation": {
            "group_key": group or f"CT{index:03d}",
            "partition": partition,
            "identity_verified": True,
            "label_verified": True,
            "label_revision": 3,
        },
    }


def test_manifest_preserves_labels_and_is_order_independent():
    rows = [sample(1), sample(2), sample(3, "VALIDATION"), sample(4, "HOLDOUT")]
    before = deepcopy(rows)
    manifest = make_manifest(rows)
    assert manifest == make_manifest(list(reversed(rows)))
    assert rows == before
    assert manifest["partitions"]["TRAIN"][0]["reading"]["final_meter_reading"] == "00120"
    assert manifest["independent_holdout"] is True


@pytest.mark.parametrize("link", ["group", "code", "customer", "sha"])
@pytest.mark.parametrize("partition", ["VALIDATION", "HOLDOUT"])
def test_aliases_and_duplicate_images_cannot_leak(link, partition):
    a, b = sample(1), sample(2, partition)
    if link == "group":
        b["annotation"]["group_key"] = a["annotation"]["group_key"]
    elif link == "sha":
        b["image"]["sha256"] = a["image"]["sha256"]
    else:
        key = "final_customer_id" if link == "code" else "matched_customer_id"
        a["reading"][key] = b["reading"][key] = "PN2.001"
    with pytest.raises(ValueError):
        make_manifest([a, b])


def test_experimental_keeps_holdout_out_and_never_claims_independence():
    holdout = sample(4, "HOLDOUT")
    unknown = [sample(i) for i in (1, 2, 3)]
    for row in unknown:
        row["annotation"] = {}
    data = make_manifest([*unknown, holdout], experimental=True)
    assert [s["image"]["id"] for s in data["partitions"]["HOLDOUT"]] == ["4"]
    assert len(data["partitions"]["TRAIN"]) == 2
    assert len(data["partitions"]["VALIDATION"]) == 1
    assert data["independent_holdout"] is False
    assert data["validation_groups_verified"] is False
    assert data["unknown_meter_identity_samples"] == 3


def test_updated_reading_invalidates_verification():
    row = sample(1)
    row["reading"]["revision"] += 1
    assert sample_issues(row)
    assert not make_manifest([row])["partitions"]["TRAIN"]


@pytest.mark.parametrize("label", ["１２３４５", "12345.2", "123", "123456789", "<script>", None])
def test_invalid_integer_labels_are_excluded(label):
    row = sample(1)
    row["reading"]["final_meter_reading"] = label
    assert not make_manifest([row])["partitions"]["TRAIN"]


def test_invalid_polygon_is_not_verified():
    row = sample(1)
    row["reading"]["meter_polygon_json"] = {"points": []}
    assert sample_issues(row)
    assert not make_manifest([row])["partitions"]["TRAIN"]


def test_reading_region_outside_meter_is_not_verified():
    row = sample(1)
    row["reading"]["meter_polygon_json"] = {
        "points": [{"x": x, "y": y} for x, y in ((0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8))]
    }
    assert any("ngoài" in issue for issue in sample_issues(row))
    assert not make_manifest([row])["partitions"]["TRAIN"]


def test_group_is_normalized_and_paths_are_rejected():
    payload = DatasetAnnotationRequest(
        expected_revision=0, expected_label_revision=3, group_key=" ct001 ", partition="TRAIN"
    )
    assert payload.group_key == "CT001"
    with pytest.raises(ValidationError):
        DatasetAnnotationRequest(expected_revision=0, expected_label_revision=3, group_key="../etc")


@pytest.mark.parametrize(
    "options",
    [{"epochs": 0}, {"batch_size": 1000}, {"learning_rate": float("nan")}, {"learning_rate": 0.1}],
)
def test_training_options_are_bounded(options):
    with pytest.raises(ValidationError):
        TrainingStartRequest(**options)
