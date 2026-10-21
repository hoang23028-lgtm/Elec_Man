"""Production sequence readers for mechanical meter integer wheels."""

import json
import re
import sys
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import cv2
import numpy as np


def normalize_prediction(text: str, integer_digits: int) -> str | None:
    """Extract one numeric register and discard one unseparated red wheel."""
    compact = re.sub(r"\s+", "", text)
    match = re.fullmatch(r"([0-9]{4,9})(?:[.,]([0-9]))?", compact)
    if match is not None:
        integer = match.group(1)
    else:
        # OCR may retain nearby printed letters even after a correct region crop.
        # Consensus with the second reader still prevents this tolerant extraction
        # from becoming an automatic answer on its own.
        digit_runs = re.findall(r"[0-9]+", compact)
        if len(digit_runs) != 1:
            return None
        integer = digit_runs[0]
    if len(integer) == integer_digits:
        return integer
    if len(integer) == integer_digits + 1 and (match is None or match.group(2) is None):
        return integer[:integer_digits]
    return None


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


class PaddleV6SmallReader:
    name = "PP-OCRv6_small_rec"

    def __init__(self) -> None:
        from paddleocr import TextRecognition

        self.model = TextRecognition(model_name=self.name, device="cpu")

    def predict(
        self, image: np.ndarray, integer_digits: int
    ) -> tuple[str | None, float]:
        result = next(iter(self.model.predict(input=image, batch_size=1)))
        payload = result.json
        if callable(payload):
            payload = payload()
        if isinstance(payload, str):
            payload = json.loads(payload)
        values = payload.get("res", payload)
        text = str(values.get("rec_text", ""))
        score = float(values.get("rec_score", 0.0))
        return normalize_prediction(text, integer_digits), score


class ParseqTinyReader:
    name = "parseq_tiny"

    def __init__(self, repository: Path, encoder_path: Path | None = None) -> None:
        sys.path.insert(0, str(repository.resolve()))
        import torch
        from torchvision import transforms

        self.torch = torch
        self.model = torch.hub.load(
            str(repository.resolve()), self.name, source="local", pretrained=True
        ).eval()
        self._base_state = None
        self._checkpoint_signature = None
        self._encoder_session = None
        self._encoder_enabled = False
        self._encoder_hash = None
        if encoder_path:
            from ai.readers.encoder_onnx import EncoderSession, encoder_digest

            self._encoder_session = EncoderSession(encoder_path)
            self._encoder_hash = encoder_digest(self.model)
        self.transform = transforms.Compose(
            [
                transforms.Resize(
                    self.model.hparams.img_size,
                    transforms.InterpolationMode.BICUBIC,
                ),
                transforms.ToTensor(),
                transforms.Normalize(0.5, 0.5),
            ]
        )

    def load_checkpoint(self, path: Path, expected_sha256: str):
        from safetensors import safe_open
        from safetensors.torch import load_file

        signature = (
            str(path),
            path.stat().st_mtime_ns,
            path.stat().st_size,
            expected_sha256,
        )
        if signature == self._checkpoint_signature:
            return
        if (
            path.suffix != ".safetensors"
            or path.stat().st_size > 100 * 1024**2
            or sha256(path.read_bytes()).hexdigest() != expected_sha256
        ):
            raise ValueError("Artifact bộ đọc không hợp lệ hoặc checksum không khớp.")
        with safe_open(str(path), framework="pt", device="cpu") as file:
            metadata = file.metadata() or {}
        if (
            metadata.get("base_model") != "parseq_tiny"
            or metadata.get("base_revision")
            != "1902db043c029a7e03a3818c616c06600af574be"
        ):
            raise ValueError("Artifact không tương thích PARSeq-tiny đã đóng gói.")
        state = load_file(str(path), device="cpu")
        expected = self.model.state_dict()
        if set(state) != set(expected) or any(
            tensor.shape != expected[name].shape or tensor.dtype != expected[name].dtype
            for name, tensor in state.items()
        ):
            raise ValueError("Cấu trúc trọng số không khớp kiến trúc đã đóng gói.")
        if any(not self.torch.isfinite(tensor).all() for tensor in state.values()):
            raise ValueError("Trọng số bộ đọc không hữu hạn.")
        if self._base_state is None:
            self._base_state = {
                name: tensor.detach().cpu().clone()
                for name, tensor in self.model.state_dict().items()
            }
        self.model.load_state_dict(state, strict=True)
        self.model.eval()
        self._checkpoint_signature = signature
        self._refresh_encoder_hash()

    def reset_checkpoint(self):
        if self._checkpoint_signature is not None and self._base_state is not None:
            self.model.load_state_dict(self._base_state, strict=True)
            self.model.eval()
            self._checkpoint_signature = None
            self._refresh_encoder_hash()

    def _refresh_encoder_hash(self):
        if self._encoder_session:
            from ai.readers.encoder_onnx import encoder_digest

            self._encoder_hash = encoder_digest(self.model)

    def set_encoder_runtime(self, runtime):
        if runtime not in {"torch", "onnx"}:
            raise ValueError("Runtime encoder không hợp lệ.")
        if runtime == "onnx" and (
            not self._encoder_session
            or self._encoder_hash != self._encoder_session.encoder_sha256
        ):
            raise ValueError("Không có encoder ONNX tương đương trọng số hiện tại.")
        self._encoder_enabled = runtime == "onnx"

    def predict(
        self, image: np.ndarray, integer_digits: int
    ) -> tuple[str | None, float]:
        from PIL import Image

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        tensor = self.transform(Image.fromarray(rgb)).unsqueeze(0)
        original = self.model.model.encode
        try:
            if self._encoder_enabled:
                self.model.model.encode = self._encoder_session.encode
            with self.torch.inference_mode():
                probabilities = self.model(tensor).softmax(-1)
        finally:
            self.model.model.encode = original
        if not self.torch.isfinite(probabilities).all():
            return None, 0.0
        labels, scores = self.model.tokenizer.decode(probabilities)
        score = float(scores[0].mean().item()) if scores[0].numel() else 0.0
        return normalize_prediction(labels[0], integer_digits), score
