from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from ai.pipeline.detector import MeterDetector
from ai.pipeline.preprocessing import prepare_for_detection

WIDTH = 20
HEIGHT = 32
HOG_FEATURE_SIZE = 756


def _normalized_gray(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    resized = cv2.resize(gray, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(resized)


def _raw_feature(image: np.ndarray) -> np.ndarray:
    return (_normalized_gray(image).astype(np.float32) / 255.0).reshape(-1)


def _hog_feature(image: np.ndarray) -> np.ndarray:
    descriptor = cv2.HOGDescriptor(
        (WIDTH, HEIGHT),
        (10, 8),
        (5, 4),
        (5, 4),
        9,
    )
    feature = descriptor.compute(_normalized_gray(image)).reshape(-1).astype(np.float32)
    if feature.size != HOG_FEATURE_SIZE:
        raise ValueError("Kích thước đặc trưng HOG không hợp lệ.")
    return feature


def _augment_crop(image: np.ndarray) -> list[np.ndarray]:
    height, width = image.shape[:2]
    variants = [image]
    for horizontal_shift in (-1, 1):
        transform = np.float32([[1, 0, horizontal_shift], [0, 1, 0]])
        variants.append(
            cv2.warpAffine(
                image,
                transform,
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
        )
    variants.extend(
        [
            cv2.convertScaleAbs(image, alpha=0.85, beta=0),
            cv2.convertScaleAbs(image, alpha=1.15, beta=0),
        ]
    )
    return variants


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


def sample_features(
    path: Path, reading: str, *, augment: bool = False
) -> list[tuple[int, np.ndarray]]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    digits = "".join(character for character in reading if character.isdigit())
    if image is None or not 4 <= len(digits) <= 8:
        return []
    crops = digit_crops(image, len(digits))
    if len(crops) != len(digits):
        return []
    samples: list[tuple[int, np.ndarray]] = []
    for label, crop in zip(digits, crops, strict=True):
        variants = _augment_crop(crop) if augment else [crop]
        samples.extend((int(label), _hog_feature(variant)) for variant in variants)
    return samples


def reading_features(
    image: np.ndarray, digit_count: int, feature_mode: str = "hog"
) -> list[np.ndarray]:
    extractor = _raw_feature if feature_mode == "raw" else _hog_feature
    return [extractor(crop) for crop in digit_crops(image, digit_count)]


class DigitModel(Protocol):
    feature_mode: str

    def predict_features(self, features: list[np.ndarray]) -> tuple[str, float]: ...


@dataclass(frozen=True)
class DigitCentroidModel:
    feature_mode = "raw"
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


@dataclass(frozen=True)
class DigitHogSoftmaxModel:
    feature_mode = "hog"
    labels: np.ndarray
    weights: np.ndarray
    bias: np.ndarray
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def train(
        cls,
        features: list[np.ndarray],
        targets: list[int],
        *,
        seed: int,
        epochs: int = 80,
        batch_size: int = 256,
    ) -> "DigitHogSoftmaxModel":
        if not features or len(features) != len(targets):
            raise ValueError("Dữ liệu đặc trưng và nhãn không hợp lệ.")
        matrix = np.stack(features).astype(np.float32)
        labels = np.array(sorted(set(targets)), dtype=np.int64)
        if labels.size < 2:
            raise ValueError("Cần ít nhất hai lớp chữ số để huấn luyện.")
        mean = matrix.mean(axis=0)
        scale = matrix.std(axis=0)
        scale[scale < 1e-6] = 1.0
        normalized = (matrix - mean) / scale
        label_indexes = np.searchsorted(labels, np.asarray(targets, dtype=np.int64))
        sample_counts = np.bincount(label_indexes, minlength=labels.size).astype(
            np.float32
        )
        class_weights = matrix.shape[0] / (labels.size * sample_counts)
        sample_weights = class_weights[label_indexes]
        sample_weights /= sample_weights.mean()

        generator = np.random.default_rng(seed)
        weights = generator.normal(0, 0.005, (matrix.shape[1], labels.size)).astype(
            np.float32
        )
        bias = np.zeros(labels.size, dtype=np.float32)
        learning_rate = 0.12
        regularization = 1e-4
        for epoch in range(epochs):
            order = generator.permutation(matrix.shape[0])
            for start in range(0, matrix.shape[0], batch_size):
                indexes = order[start : start + batch_size]
                batch = normalized[indexes]
                encoded = np.eye(labels.size, dtype=np.float32)[label_indexes[indexes]]
                logits = batch @ weights + bias
                logits -= logits.max(axis=1, keepdims=True)
                probabilities = np.exp(logits)
                probabilities /= probabilities.sum(axis=1, keepdims=True)
                error = (probabilities - encoded) * sample_weights[indexes, None]
                gradient = batch.T @ error / indexes.size
                weights -= learning_rate * (gradient + regularization * weights)
                bias -= learning_rate * error.mean(axis=0)
            if epoch and epoch % 20 == 0:
                learning_rate *= 0.7
        return cls(labels, weights, bias, mean, scale)

    @classmethod
    def load(cls, path: Path) -> "DigitHogSoftmaxModel":
        with np.load(path, allow_pickle=False) as data:
            model = cls(
                data["labels"].astype(np.int64),
                data["weights"].astype(np.float32),
                data["bias"].astype(np.float32),
                data["mean"].astype(np.float32),
                data["scale"].astype(np.float32),
            )
        if (
            model.weights.ndim != 2
            or model.weights.shape[0] != model.mean.size
            or model.weights.shape[0] != model.scale.size
            or model.weights.shape[1] != model.labels.size
            or model.bias.size != model.labels.size
            or not np.all(np.isfinite(model.weights))
            or not np.all(np.isfinite(model.bias))
            or not np.all(np.isfinite(model.mean))
            or not np.all(np.isfinite(model.scale))
            or np.any(model.scale <= 0)
            or np.unique(model.labels).size != model.labels.size
        ):
            raise ValueError("Artifact mô hình chữ số không hợp lệ.")
        return model

    def save(self, path: Path) -> None:
        np.savez_compressed(
            path,
            labels=self.labels,
            weights=self.weights,
            bias=self.bias,
            mean=self.mean,
            scale=self.scale,
        )

    def predict_features(self, features: list[np.ndarray]) -> tuple[str, float]:
        if not features:
            return "", 0.0
        matrix = np.stack(features).astype(np.float32)
        if matrix.shape[1] != self.mean.size:
            return "", 0.0
        logits = ((matrix - self.mean) / self.scale) @ self.weights + self.bias
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        best = np.argmax(probabilities, axis=1)
        prediction = "".join(str(int(self.labels[index])) for index in best)
        confidence = float(np.mean(probabilities[np.arange(best.size), best]))
        return prediction, max(0.0, min(0.99, confidence))


def load_digit_model(path: Path) -> DigitModel:
    with np.load(path, allow_pickle=False) as data:
        keys = set(data.files)
    if {"weights", "bias", "mean", "scale"}.issubset(keys):
        return DigitHogSoftmaxModel.load(path)
    if "centroids" in keys:
        return DigitCentroidModel.load(path)
    raise ValueError("Không nhận diện được định dạng artifact mô hình chữ số.")
