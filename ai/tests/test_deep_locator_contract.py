from types import SimpleNamespace

import numpy as np
import onnxruntime as ort
import pytest

from ai.training.deep_locator import (
    ARCHITECTURE,
    DeepRegionLocator,
    image_tensor,
    train_deep_locator,
)


def test_retired_architecture_cannot_be_trained_again(tmp_path):
    with pytest.raises(TypeError):
        train_deep_locator(
            [],
            [],
            tmp_path / "retired.onnx",
            coordinate_space="image",
            architecture="mobilenet-v3-small-spatial-keypoints-v1",
        )
    assert not (tmp_path / "retired.onnx").exists()


@pytest.mark.parametrize(
    "architecture,size",
    [("mobilenet-v3-small-spatial-keypoints-v1", 192), (ARCHITECTURE, 320)],
)
def test_locator_keeps_explicit_v1_v2_input_contract(
    tmp_path, monkeypatch, architecture, size
):
    path = tmp_path / "model.onnx"
    path.write_bytes(b"fixture-not-an-onnx-graph")
    meta = {
        "architecture": architecture,
        "coordinate_space": "meter",
        "validation_error": "0.02",
    }
    calls = []

    def infer(_, feed):
        calls.append(feed["image"].shape)
        return [np.array([[0.1, 0.2, 0.9, 0.2, 0.9, 0.5, 0.1, 0.5]], np.float32)]

    session = SimpleNamespace(
        get_modelmeta=lambda: SimpleNamespace(custom_metadata_map=meta),
        get_inputs=lambda: [
            SimpleNamespace(
                name="image", shape=[1, 3, size, size], type="tensor(float)"
            )
        ],
        get_outputs=lambda: [SimpleNamespace(shape=[1, 8])],
        run=infer,
    )
    monkeypatch.setattr(ort, "InferenceSession", lambda *a, **kw: session)
    model = DeepRegionLocator(path)
    assert model.predict(np.zeros((100, 200, 3), np.uint8)) is not None
    assert calls == [(1, 3, size, size)]


def test_image_tensor_is_finite_rgb_normalized_with_explicit_resolution():
    image = np.zeros((50, 100, 3), np.uint8)
    image[:, :, 2] = 255
    tensor = image_tensor(image, 320)
    assert tensor.shape == (3, 320, 320) and tensor.dtype == np.float32
    assert np.isfinite(tensor).all() and tensor[0, 0, 0] > tensor[2, 0, 0]
