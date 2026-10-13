from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from ai.training.dataset import export_sequence_dataset, split_by_meter, split_metadata


def rows_for(codes):
    return [
        (SimpleNamespace(sha256=str(index)), SimpleNamespace(final_customer_id=code))
        for index, code in enumerate(codes)
    ]


def test_split_keeps_customer_groups_disjoint_and_is_order_independent():
    rows = rows_for(["PN2.001", "pn2.001", "PN2.002", "PN2.002", "PN2.003", "PN2.003"])
    train, validation = split_by_meter(rows)
    assert {r.final_customer_id.upper() for _, r in train}.isdisjoint(
        {r.final_customer_id.upper() for _, r in validation}
    )
    second_train, second_validation = split_by_meter(list(reversed(rows)))
    assert {i.sha256 for i, _ in train} == {i.sha256 for i, _ in second_train}
    assert {i.sha256 for i, _ in validation} == {i.sha256 for i, _ in second_validation}
    assert len(train) + len(validation) == len(rows)


def test_single_customer_cannot_be_split_by_fallback():
    with pytest.raises(ValueError, match="hai nhóm"):
        split_by_meter(rows_for(["PN2.001"] * 10))


def test_mixed_uuid_and_customer_code_aliases_remain_in_one_partition():
    rows = rows_for(["PN2.001", "pn2.001", "PN2.002", "PN2.002", "PN2.003", "PN2.003"])
    rows[0][1].matched_customer_id = "customer-1"
    train, validation = split_by_meter(rows)
    for left, right in ((0, 1), (2, 3), (4, 5)):
        assert (rows[left] in train) == (rows[right] in train)
        assert (rows[left] in validation) == (rows[right] in validation)
    assert split_metadata(rows)["validation_groups_verified"] is True
    rows[0][1].final_customer_id = ""
    assert split_metadata(rows)["unknown_meter_identity_samples"] == 0
    rows[1][1].final_customer_id = ""
    assert split_metadata(rows)["validation_groups_verified"] is False


def test_unknown_meter_identity_is_not_claimed_as_an_independent_holdout():
    rows = rows_for([None, None, None, None, None])
    metadata = split_metadata(rows)
    assert metadata["unknown_meter_identity_samples"] == 5
    assert metadata["validation_groups_verified"] is False
    assert metadata["independent_holdout"] is False


def test_export_sequence_dataset_writes_deterministic_crops(tmp_path: Path):
    storage = tmp_path / "storage"
    storage.mkdir()
    image = np.full((100, 220, 3), 180, dtype=np.uint8)
    cv2.rectangle(image, (20, 25), (200, 70), (245, 245, 245), -1)
    rows = []
    for index, label in enumerate(("01234", "56789", "13579")):
        relative_path = f"meter-{index}.png"
        path = storage / relative_path
        assert cv2.imwrite(str(path), image)
        rows.append(
            (
                SimpleNamespace(sha256=f"sha-{index}", relative_path=relative_path),
                SimpleNamespace(
                    final_meter_reading=label,
                    reading_polygon_json={
                        "points": [
                            {"x": 0.09, "y": 0.25},
                            {"x": 0.91, "y": 0.25},
                            {"x": 0.91, "y": 0.7},
                            {"x": 0.09, "y": 0.7},
                        ]
                    },
                ),
            )
        )

    result = export_sequence_dataset(rows[:2], rows[2:], storage, tmp_path / "dataset")

    assert result["train_samples"] == 2
    assert result["validation_samples"] == 1
    assert len(result["manifest_sha256"]) == 64
    assert (tmp_path / "dataset/train.tsv").read_text(encoding="utf-8").count("\n") == 2
    assert (tmp_path / "dataset/validation/sha-2.png").is_file()
