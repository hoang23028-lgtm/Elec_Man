"""Offline smoke only; no database, real labels or accuracy claim."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from ai.readers.sequence import ParseqTinyReader
from ai.training.deep_locator import train_deep_locator


def main():
    with TemporaryDirectory(prefix="locator-onnx-smoke-") as directory:
        rows = [
            (
                np.full((120, 200, 3), 90 + i * 30, np.uint8),
                (
                    (0.1 + i * 0.01, 0.1),
                    (0.85, 0.1 + i * 0.01),
                    (0.85, 0.8),
                    (0.1, 0.8),
                ),
            )
            for i in range(3)
        ]
        model, metrics = train_deep_locator(
            rows[:2],
            rows[2:],
            Path(directory) / "model.onnx",
            coordinate_space="image",
            epochs=2,
            max_seconds=120,
        )
        assert model.predict(rows[2][0]) is not None and metrics["onnx_parity"]
        reader = ParseqTinyReader(Path("/opt/parseq"), Path("/opt/parseq-encoder.onnx"))
        import torch

        torch.set_num_threads(1)
        maximum_error = 0
        for seed in range(3):
            torch.manual_seed(seed)
            tensor = torch.randn(1, 3, *reader.model.hparams.img_size)
            with torch.inference_mode():
                native = reader.model.model.encode(tensor)
                exported = reader._encoder_session.encode(tensor)
            assert torch.allclose(native, exported, rtol=1e-3, atol=1e-4)
            maximum_error = max(maximum_error, float((native - exported).abs().max()))
        torch_values = [reader.predict(row[0], 5) for row in rows]
        reader.set_encoder_runtime("onnx")
        onnx_values = [reader.predict(row[0], 5) for row in rows]
        assert all(
            a[0] == b[0] and abs(a[1] - b[1]) < 1e-4
            for a, b in zip(torch_values, onnx_values, strict=True)
        )
        reader._encoder_hash = "incompatible"
        try:
            reader.set_encoder_runtime("onnx")
        except ValueError:
            pass
        else:
            raise AssertionError("Mismatched encoder accepted")
        print(
            json.dumps(
                {
                    "deep_locator_train_export": True,
                    "onnx_prediction": True,
                    "encoder_max_error": maximum_error,
                    "encoder_value_parity": True,
                    "incompatible_encoder_rejected": True,
                    "scope": "synthetic_smoke_not_accuracy",
                }
            )
        )


if __name__ == "__main__":
    main()
