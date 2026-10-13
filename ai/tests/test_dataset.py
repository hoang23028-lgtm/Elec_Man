from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from ai.training.dataset import export_sequence_dataset


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
