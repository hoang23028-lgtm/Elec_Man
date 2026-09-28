from pathlib import Path

import cv2
import numpy as np

from ai.pipeline.geometry import perspective_crop
from ai.training.digit_model import (
    DigitCentroidModel,
    DigitHogSoftmaxModel,
    HOG_FEATURE_SIZE,
    digit_crops,
    integer_register_strip,
    load_digit_model,
    reading_features,
)
from ai.training.region_model import ReadingRegionRegressor, region_features


def test_digit_crops_follow_verified_integer_length() -> None:
    image = np.full((400, 600, 3), 180, dtype=np.uint8)
    crops = digit_crops(image, 5)
    assert len(crops) == 5
    assert all(crop.size > 0 for crop in crops)


def test_digit_crops_use_human_verified_region() -> None:
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    image[:, 100:] = 255

    crops = digit_crops(image, 5, (0.5, 0.0, 0.5, 1.0))

    assert len(crops) == 5
    assert all(float(crop.mean()) == 255 for crop in crops)


def test_integer_register_strip_removes_red_fractional_wheel() -> None:
    strip = np.full((40, 120, 3), 120, dtype=np.uint8)
    strip[5:34, 100:118] = (0, 0, 230)

    integer_strip = integer_register_strip(strip)
    crops = digit_crops(integer_strip, 5, (0.0, 0.0, 1.0, 1.0))

    assert integer_strip.shape[1] < 100
    assert len(crops) == 5
    assert all(float(crop[:, :, 2].mean()) < 180 for crop in crops)


def test_perspective_crop_rectifies_four_point_region() -> None:
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    vertices = np.array([[40, 30], [170, 20], [160, 70], [30, 80]], dtype=np.int32)
    cv2.fillConvexPoly(image, vertices, (255, 255, 255))

    crop = perspective_crop(
        image,
        ((0.2, 0.3), (0.85, 0.2), (0.8, 0.7), (0.15, 0.8)),
    )

    assert crop.shape[1] >= 130
    assert crop.shape[0] >= 50
    assert float(crop.mean()) > 245


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


def test_region_regressor_learns_verified_four_corners() -> None:
    images = [
        np.full((80, 120, 3), value, dtype=np.uint8) for value in (80, 100, 120, 140)
    ]
    target = np.array(
        [[0.2, 0.3], [0.8, 0.25], [0.78, 0.55], [0.22, 0.6]], dtype=np.float32
    )
    model = ReadingRegionRegressor.train(
        [region_features(image) for image in images],
        [target.copy() for _ in images],
    ).with_validation_error(0.02)

    prediction = model.predict(images[1])

    assert prediction is not None
    polygon, confidence = prediction
    assert np.mean(np.abs(np.asarray(polygon) - target)) < 0.02
    assert confidence >= 0.9


def test_specialized_model_round_trips_region_metadata(tmp_path: Path) -> None:
    digit_model = DigitHogSoftmaxModel.train(
        [np.zeros(4, dtype=np.float32)] * 4 + [np.ones(4, dtype=np.float32)] * 4,
        [0] * 4 + [1] * 4,
        seed=7,
        epochs=20,
    )
    images = [np.full((80, 120, 3), value, dtype=np.uint8) for value in (80, 120, 160)]
    target = np.array(
        [[0.2, 0.3], [0.8, 0.25], [0.78, 0.55], [0.22, 0.6]], dtype=np.float32
    )
    region_model = ReadingRegionRegressor.train(
        [region_features(image) for image in images],
        [target.copy() for _ in images],
    ).with_validation_error(0.02)
    model = digit_model.with_training_metadata([5, 5, 6], region_model)
    path = tmp_path / "region-model.npz"
    model.save(path)

    loaded = load_digit_model(path)
    prediction = loaded.predict_region(images[1])

    assert loaded.candidate_lengths() == (5, 6)
    assert prediction is not None
    assert np.mean(np.abs(np.asarray(prediction[0]) - target)) < 0.02
