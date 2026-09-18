"""Shared pretrained scene-OCR engine."""

from dataclasses import dataclass

import numpy as np
from rapidocr_onnxruntime import RapidOCR


@dataclass(frozen=True)
class TextLine:
    box: tuple[tuple[float, float], ...]
    text: str
    confidence: float


_engine: RapidOCR | None = None


def read_lines(image: np.ndarray) -> list[TextLine]:
    global _engine
    if _engine is None:
        _engine = RapidOCR()
    raw_lines, _ = _engine(image)
    if not raw_lines:
        return []
    return [
        TextLine(tuple((float(point[0]), float(point[1])) for point in box), str(text), float(confidence))
        for box, text, confidence in raw_lines
    ]
