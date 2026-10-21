from unittest.mock import Mock

import numpy as np

from ai.pipeline.geometry import transform_polygon
from ai.training.locator_samples import register_samples

FRAME = ((0.2, 0.1), (0.8, 0.1), (0.8, 0.9), (0.2, 0.9))
READING = ((0.3, 0.35), (0.7, 0.35), (0.7, 0.45), (0.3, 0.45))


def test_validation_register_crop_uses_predicted_frame_without_ground_truth_hint():
    predictor = Mock()
    predictor.predict_region.return_value = (FRAME, 0.8)
    image = np.zeros((200, 300, 3), np.uint8)
    samples = list(register_samples(image, READING, predictor))
    assert len(samples) == 1
    assert np.allclose(samples[0][1], transform_polygon(READING, FRAME))
    predictor.predict_region.assert_called_once_with(image)


def test_training_adds_reproducible_frame_noise_and_reprojects_same_reading():
    predictor = Mock()
    predictor.predict_region.return_value = (FRAME, 0.8)
    image = np.zeros((200, 300, 3), np.uint8)
    a = list(register_samples(image, READING, predictor, training_frame=FRAME))
    b = list(register_samples(image, READING, predictor, training_frame=FRAME))
    assert len(a) == 4 and len(b) == 4
    assert all(np.allclose(x[1], y[1]) for x, y in zip(a, b, strict=True))
    assert not np.allclose(a[0][1], a[-1][1])
    assert all(np.isfinite(target).all() for _, target in a)
