from pathlib import Path

import numpy as np

from ai.training.digit_model import DigitCentroidModel, digit_crops


def test_digit_crops_follow_verified_integer_length() -> None:
    image = np.full((400, 600, 3), 180, dtype=np.uint8)
    crops = digit_crops(image, 5)
    assert len(crops) == 5
    assert all(crop.size > 0 for crop in crops)


def test_centroid_model_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "model.npz"
    np.savez_compressed(
        path,
        labels=np.array([1, 7], dtype=np.int64),
        centroids=np.stack(
            [np.zeros(640, dtype=np.float32), np.ones(640, dtype=np.float32)]
        ),
    )
    model = DigitCentroidModel.load(path)
    prediction, confidence = model.predict_features([np.ones(640, dtype=np.float32)])
    assert prediction == "7"
    assert confidence > 0.9
