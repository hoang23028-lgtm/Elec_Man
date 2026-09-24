"""Small, dependency-free wrapper around the Tesseract CLI bundled in the worker."""

from dataclasses import dataclass
from pathlib import Path

# The executable is fixed and invoked with an argument list; shell execution is disabled.
from subprocess import run  # nosec B404
from tempfile import TemporaryDirectory

import cv2
import numpy as np


@dataclass(frozen=True)
class OcrCandidate:
    text: str
    confidence: float


def read(image: np.ndarray, *, psm: int, whitelist: str | None = None) -> OcrCandidate:
    if image.size == 0:
        return OcrCandidate("", 0.0)
    if whitelist is not None and (
        len(whitelist) > 128
        or not whitelist.isascii()
        or any(char.isspace() for char in whitelist)
    ):
        raise ValueError("Danh sách ký tự OCR không hợp lệ.")
    with TemporaryDirectory(prefix="meter-ocr-") as directory:
        input_path = Path(directory) / "input.png"
        output_base = Path(directory) / "result"
        if not cv2.imwrite(str(input_path), image):
            return OcrCandidate("", 0.0)
        command = [
            "tesseract",
            str(input_path),
            str(output_base),
            "--psm",
            str(psm),
            "tsv",
        ]
        if whitelist:
            command.extend(["-c", f"tessedit_char_whitelist={whitelist}"])
        # Variable arguments are validated temporary paths and bounded OCR options.
        completed = run(  # nosec B603
            command, capture_output=True, text=True, timeout=20, check=False
        )
        tsv_path = output_base.with_suffix(".tsv")
        if completed.returncode != 0 or not tsv_path.is_file():
            return OcrCandidate("", 0.0)
        words: list[str] = []
        confidences: list[float] = []
        for line in tsv_path.read_text(encoding="utf-8", errors="replace").splitlines()[
            1:
        ]:
            columns = line.split("\t", 11)
            if len(columns) != 12 or not columns[11].strip():
                continue
            words.append(columns[11].strip())
            try:
                confidence = float(columns[10])
            except ValueError:
                confidence = -1
            if confidence >= 0:
                confidences.append(confidence / 100)
        return OcrCandidate(
            " ".join(words), sum(confidences) / len(confidences) if confidences else 0.0
        )


def enhanced_variants(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    scale = max(1.0, 1400 / max(gray.shape))
    if scale > 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
    threshold = cv2.adaptiveThreshold(
        clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9
    )
    return [clahe, threshold]
