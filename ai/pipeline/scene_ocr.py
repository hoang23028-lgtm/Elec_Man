"""Shared RapidOCR engine for full-scene text detection and recognition."""

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
        # The worker is CPU-quota bounded. Three default ORT thread pools can
        # oversubscribe it heavily when reader services run at the same time.
        _engine = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    raw_lines, _ = _engine(image)
    if not raw_lines:
        return []
    return [
        TextLine(
            tuple((float(point[0]), float(point[1])) for point in box),
            str(text),
            float(confidence),
        )
        for box, text, confidence in raw_lines
    ]
