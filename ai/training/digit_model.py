from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ai.pipeline.detector import MeterDetector
from ai.pipeline.preprocessing import prepare_for_detection

WIDTH = 20
HEIGHT = 32


def _feature(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    resized = cv2.resize(gray, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    normalized = cv2.equalizeHist(resized)
    return (normalized.astype(np.float32) / 255.0).reshape(-1)


def digit_crops(image: np.ndarray, digit_count: int) -> list[np.ndarray]:
    prepared = prepare_for_detection(image)
    region = MeterDetector().detect(prepared).reading_region
    if region is None:
        return []
    x, y, width, height = region
    strip = prepared[y : y + height, x : x + width]
    if strip.size == 0 or digit_count <= 0:
        return []
    # The detector returns the mechanical register strip. Split by the verified
    # integer-wheel count; fractional/red wheels are absent from the label.
    edges = np.linspace(0, strip.shape[1], digit_count + 1, dtype=int)
    return [strip[:, edges[index] : edges[index + 1]] for index in range(digit_count)]


def sample_features(path: Path, reading: str) -> list[tuple[int, np.ndarray]]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    digits = "".join(character for character in reading if character.isdigit())
    if image is None or not 4 <= len(digits) <= 8:
        return []
    crops = digit_crops(image, len(digits))
    if len(crops) != len(digits):
        return []
    return [
        (int(label), _feature(crop)) for label, crop in zip(digits, crops, strict=True)
    ]


def reading_features(image: np.ndarray, digit_count: int) -> list[np.ndarray]:
    return [_feature(crop) for crop in digit_crops(image, digit_count)]


@dataclass(frozen=True)
class DigitCentroidModel:
    labels: np.ndarray
    centroids: np.ndarray

    @classmethod
    def load(cls, path: Path) -> "DigitCentroidModel":
        with np.load(path, allow_pickle=False) as data:
            return cls(
                data["labels"].astype(np.int64), data["centroids"].astype(np.float32)
            )

    def predict_features(self, features: list[np.ndarray]) -> tuple[str, float]:
        if not features:
            return "", 0.0
        predictions: list[str] = []
        confidences: list[float] = []
        for feature in features:
            distances = np.mean((self.centroids - feature) ** 2, axis=1)
            best = int(np.argmin(distances))
            predictions.append(str(int(self.labels[best])))
            confidences.append(max(0.0, min(0.99, 1.0 - float(distances[best]) * 3.0)))
        return "".join(predictions), float(np.mean(confidences))
