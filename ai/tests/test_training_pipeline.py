from pathlib import Path

import numpy as np

from ai.training.digit_model import (
    DigitCentroidModel,
    DigitHogSoftmaxModel,
    HOG_FEATURE_SIZE,
    digit_crops,
    load_digit_model,
    reading_features,
)


def test_digit_crops_follow_verified_integer_length() -> None:
    image = np.full((400, 600, 3), 180, dtype=np.uint8)
    crops = digit_crops(image, 5)
    assert len(crops) == 5
    assert all(crop.size > 0 for crop in crops)


def test_hog_features_have_stable_shape() -> None:
    image = np.full((400, 600, 3), 180, dtype=np.uint8)

    features = reading_features(image, 5, "hog")

    assert len(features) == 5
    assert all(feature.shape == (HOG_FEATURE_SIZE,) for feature in features)


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


def test_specialized_softmax_model_trains_and_round_trips(tmp_path: Path) -> None:
    zero_samples = [np.array([0.0, 0.1, 0.0, 0.1], dtype=np.float32) for _ in range(8)]
    one_samples = [np.array([0.9, 1.0, 0.9, 1.0], dtype=np.float32) for _ in range(8)]
    model = DigitHogSoftmaxModel.train(
        zero_samples + one_samples,
        [0] * len(zero_samples) + [1] * len(one_samples),
        seed=42,
        epochs=200,
    )
    path = tmp_path / "specialized-model.npz"
    model.save(path)

    loaded = load_digit_model(path)
    prediction, confidence = loaded.predict_features([zero_samples[0], one_samples[0]])

    assert prediction == "01"
    assert confidence > 0.9


def test_loader_keeps_legacy_centroid_artifacts_compatible(tmp_path: Path) -> None:
    path = tmp_path / "legacy-model.npz"
    np.savez_compressed(
        path,
        labels=np.array([3, 8], dtype=np.int64),
        centroids=np.stack(
            [np.zeros(640, dtype=np.float32), np.ones(640, dtype=np.float32)]
        ),
    )

    model = load_digit_model(path)

    assert isinstance(model, DigitCentroidModel)
    assert model.feature_mode == "raw"
