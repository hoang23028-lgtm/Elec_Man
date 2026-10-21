from pathlib import Path

import cv2
import numpy as np
import pytest

from ai.pipeline.geometry import perspective_crop
from ai.pipeline.register import integer_register_strip
from ai.training.keypoint_regressor import (
    KeypointRegionRegressor,
    extract_region_features,
)


def test_integer_register_strip_removes_red_fractional_wheel() -> None:
    strip = np.full((40, 120, 3), 120, dtype=np.uint8)
    strip[5:34, 100:118] = (0, 0, 230)

    integer_strip = integer_register_strip(strip)

    assert integer_strip.shape[1] < 100
    assert float(integer_strip[:, :, 2].mean()) < 180


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


def test_region_regressor_learns_verified_four_corners() -> None:
    images = [
        np.full((80, 120, 3), value, dtype=np.uint8) for value in (80, 100, 120, 140)
    ]
    target = np.array(
        [[0.2, 0.3], [0.8, 0.25], [0.78, 0.55], [0.22, 0.6]], dtype=np.float32
    )
    model = KeypointRegionRegressor.train(
        [extract_region_features(image) for image in images],
        [target.copy() for _ in images],
    ).with_validation_error(0.02)

    prediction = model.predict(images[1])

    assert prediction is not None
    polygon, confidence = prediction
    assert np.mean(np.abs(np.asarray(polygon) - target)) < 0.02
    assert confidence >= 0.9


def test_region_regressor_round_trip(tmp_path: Path, monkeypatch) -> None:
    from ai.pipeline.preprocessing import ImagePreprocessingModel

    source_images = [
        np.full((80, 120, 3), value, dtype=np.uint8) for value in (70, 120, 170)
    ]
    images = [ImagePreprocessingModel().process(image)[0] for image in source_images]
    target = np.array(
        [[0.2, 0.3], [0.8, 0.25], [0.78, 0.55], [0.22, 0.6]], dtype=np.float32
    )
    model = KeypointRegionRegressor.train(
        [extract_region_features(image) for image in images],
        [target.copy() for _ in images],
    ).with_validation_error(0.03)
    path = tmp_path / "reading-region.npz"
    model.save(path)

    loaded = KeypointRegionRegressor.load(path)
    prediction = loaded.predict(images[1])

    assert prediction is not None
    assert np.mean(np.abs(np.asarray(prediction[0]) - target)) < 0.02

    from ai.pipeline.localization import MeterLocator, ReadingRegionLocator

    meter = MeterLocator(loaded).locate(images[1])
    region = ReadingRegionLocator(loaded).locate(images[1], meter)
    assert meter.source == "TRAINED_METER_KEYPOINTS"
    assert region.source == "TRAINED_KEYPOINTS"
    assert region.reading_polygon is not None

    from ai.pipeline import meter_pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "read_lines", lambda _: [])
    pipeline = pipeline_module.MeterReadingPipeline(
        region_model_path=path, meter_model_path=path
    )
    monkeypatch.setattr(
        pipeline.customer_code_reader, "read", lambda *_, **__: ("PN2.001", 0.9)
    )
    monkeypatch.setattr(pipeline.meter_reader, "read", lambda *_, **__: ("01234", 0.89))
    image_path = tmp_path / "meter.png"
    assert cv2.imwrite(str(image_path), source_images[1])
    result = pipeline.process(image_path)
    assert (
        result["stage_models"]["meter_location"]["source"] == "TRAINED_METER_KEYPOINTS"
    )
    assert result["stage_models"]["reading_region"]["source"] == "TRAINED_KEYPOINTS"
    assert result["meter_reading_ai"] == "01234"


@pytest.mark.parametrize("samples,features", [(3, 5), (10, 5)])
def test_ridge_solves_smaller_system_with_equivalent_weights(
    samples, features, monkeypatch
):
    rng = np.random.default_rng(42)
    x, y = (
        rng.normal(size=(samples, features)).astype(np.float32),
        rng.uniform(size=(samples, 4, 2)).astype(np.float32),
    )
    original = np.linalg.solve
    sizes = []

    def solve(a, b):
        sizes.append(a.shape[0])
        return original(a, b)

    monkeypatch.setattr(np.linalg, "solve", solve)
    model = KeypointRegionRegressor.train(list(x), list(y))
    normalized = (x - model.mean) / model.scale
    reference = normalized.T @ original(
        normalized @ normalized.T + np.eye(samples) * 2,
        y.reshape(samples, 8) - model.bias,
    )
    assert sizes == [min(samples, features)]
    assert np.allclose(model.weights, reference, atol=1e-5)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_ridge_rejects_invalid_regularization(value):
    with pytest.raises(ValueError):
        KeypointRegionRegressor.train(
            [np.ones(4), np.ones(4)],
            [np.zeros((4, 2)), np.zeros((4, 2))],
            regularization=value,
        )
