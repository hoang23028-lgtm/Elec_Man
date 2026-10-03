"""Production sequence readers for mechanical meter integer wheels."""

import json
import re
import sys
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

    def __init__(self, repository: Path) -> None:
        sys.path.insert(0, str(repository.resolve()))
        import torch
        from torchvision import transforms

        self.torch = torch
        self.model = torch.hub.load(
            str(repository.resolve()), self.name, source="local", pretrained=True
        ).eval()
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

    def predict(
        self, image: np.ndarray, integer_digits: int
    ) -> tuple[str | None, float]:
        from PIL import Image

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        tensor = self.transform(Image.fromarray(rgb)).unsqueeze(0)
        with self.torch.inference_mode():
            probabilities = self.model(tensor).softmax(-1)
        labels, scores = self.model.tokenizer.decode(probabilities)
        score = float(scores[0].mean().item()) if scores[0].numel() else 0.0
        return normalize_prediction(labels[0], integer_digits), score
