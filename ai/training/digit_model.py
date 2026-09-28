from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from ai.pipeline.detector import MeterDetector
from ai.pipeline.geometry import perspective_crop
from ai.pipeline.preprocessing import prepare_for_detection
from ai.training.region_model import ReadingRegionRegressor

WIDTH = 20
HEIGHT = 32
HOG_FEATURE_SIZE = 756


def integer_register_strip(image: np.ndarray) -> np.ndarray:
    """Remove a red fractional wheel and labels below the mechanical register."""
    if image.size == 0 or image.ndim != 3 or image.shape[1] < 20:
        return image
    height, width = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red = (
        ((hsv[:, :, 0] <= 15) | (hsv[:, :, 0] >= 165))
        & (hsv[:, :, 1] >= 55)
        & (hsv[:, :, 2] >= 60)
    )
    column_counts = red.sum(axis=0)
    minimum_column_pixels = max(2, round(height * 0.12))
    columns = np.flatnonzero(
        (column_counts >= minimum_column_pixels)
        & (np.arange(width) >= round(width * 0.45))
    )
    if columns.size < max(2, round(width * 0.025)):
        return image
    groups = np.split(columns, np.where(np.diff(columns) > 1)[0] + 1)
    group = max(groups, key=lambda item: int(column_counts[item].sum()))
    if group.size < max(2, round(width * 0.025)):
        return image
    fractional_left = int(group[0])
    if fractional_left <= round(width * 0.5):
        return image
    wheel_pixels = np.argwhere(red[:, group])
    if wheel_pixels.size == 0:
        return image
    top = max(0, int(wheel_pixels[:, 0].min()) - round(height * 0.15))
    bottom = min(height, int(wheel_pixels[:, 0].max()) + 1 + round(height * 0.12))
    right = max(1, fractional_left - round(width * 0.01))
    cropped = image[top:bottom, :right]
    return cropped if cropped.size and cropped.shape[1] >= 20 else image


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
            cv2.convertScaleAbs(image, alpha=1.0, beta=-22),
            cv2.convertScaleAbs(image, alpha=1.0, beta=22),
            cv2.GaussianBlur(image, (3, 3), 0),
        ]
    )
    center = (width / 2, height / 2)
    for angle in (-2.0, 2.0):
        variants.append(
            cv2.warpAffine(
                image,
                cv2.getRotationMatrix2D(center, angle, 1.0),
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
        )
    return variants


def digit_crops(
    image: np.ndarray,
    digit_count: int,
    reading_bbox: tuple[float, float, float, float] | None = None,
    reading_polygon: tuple[tuple[float, float], ...] | None = None,
) -> list[np.ndarray]:
    prepared = prepare_for_detection(image)
    strip = None
    if reading_polygon is not None:
        strip = perspective_crop(prepared, reading_polygon)
        region = None
    elif reading_bbox is None:
        region = MeterDetector().detect(prepared).reading_region
    else:
        image_height, image_width = prepared.shape[:2]
        normalized_x, normalized_y, normalized_width, normalized_height = reading_bbox
        x = max(0, min(image_width - 1, round(normalized_x * image_width)))
        y = max(0, min(image_height - 1, round(normalized_y * image_height)))
        right = max(
            x + 1,
            min(image_width, round((normalized_x + normalized_width) * image_width)),
        )
        bottom = max(
            y + 1,
            min(image_height, round((normalized_y + normalized_height) * image_height)),
        )
        region = (x, y, right - x, bottom - y)
    if strip is None and region is None:
        return []
    if strip is None:
        x, y, width, height = region
        strip = prepared[y : y + height, x : x + width]
    if strip.size == 0 or digit_count <= 0:
        return []
    strip = integer_register_strip(strip)
    # The detector returns the mechanical register strip. Split by the verified
    # integer-wheel count; fractional/red wheels are absent from the label.
    edges = np.linspace(0, strip.shape[1], digit_count + 1, dtype=int)
    return [strip[:, edges[index] : edges[index + 1]] for index in range(digit_count)]


def sample_features(
    path: Path,
    reading: str,
    *,
    augment: bool = False,
    reading_bbox: tuple[float, float, float, float] | None = None,
    reading_polygon: tuple[tuple[float, float], ...] | None = None,
) -> list[tuple[int, np.ndarray]]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    digits = "".join(character for character in reading if character.isdigit())
    if image is None or not 4 <= len(digits) <= 8:
        return []
    crops = digit_crops(image, len(digits), reading_bbox, reading_polygon)
    if len(crops) != len(digits):
        return []
    samples: list[tuple[int, np.ndarray]] = []
    for label, crop in zip(digits, crops, strict=True):
        variants = _augment_crop(crop) if augment else [crop]
        samples.extend((int(label), _hog_feature(variant)) for variant in variants)
    return samples


def reading_features(
    image: np.ndarray,
    digit_count: int,
    feature_mode: str = "hog",
    reading_bbox: tuple[float, float, float, float] | None = None,
    reading_polygon: tuple[tuple[float, float], ...] | None = None,
) -> list[np.ndarray]:
    extractor = _raw_feature if feature_mode == "raw" else _hog_feature
    return [
        extractor(crop)
        for crop in digit_crops(image, digit_count, reading_bbox, reading_polygon)
    ]


class DigitModel(Protocol):
    feature_mode: str

    def predict_features(self, features: list[np.ndarray]) -> tuple[str, float]: ...

    def candidate_lengths(self) -> tuple[int, ...]: ...

    def predict_region(
        self, image: np.ndarray
    ) -> tuple[tuple[tuple[float, float], ...], float] | None: ...


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

    def candidate_lengths(self) -> tuple[int, ...]:
        return (5, 6, 4, 7, 8)

    def predict_region(
        self, image: np.ndarray
    ) -> tuple[tuple[tuple[float, float], ...], float] | None:
        return None


@dataclass(frozen=True)
class DigitHogSoftmaxModel:
    feature_mode = "hog"
    labels: np.ndarray
    weights: np.ndarray
    bias: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    reading_lengths: np.ndarray | None = None
    reading_length_counts: np.ndarray | None = None
    region_model: ReadingRegionRegressor | None = None

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
            region_model = None
            if {
                "region_weights",
                "region_bias",
                "region_mean",
                "region_scale",
                "region_distance_threshold",
                "region_validation_error",
            }.issubset(data.files):
                region_model = ReadingRegionRegressor(
                    data["region_weights"].astype(np.float32),
                    data["region_bias"].astype(np.float32),
                    data["region_mean"].astype(np.float32),
                    data["region_scale"].astype(np.float32),
                    float(data["region_distance_threshold"][0]),
                    float(data["region_validation_error"][0]),
                )
                if (
                    region_model.weights.ndim != 2
                    or region_model.weights.shape
                    != (region_model.mean.size, region_model.bias.size)
                    or region_model.bias.shape != (8,)
                    or region_model.mean.ndim != 1
                    or region_model.scale.shape != region_model.mean.shape
                    or not np.all(np.isfinite(region_model.weights))
                    or not np.all(np.isfinite(region_model.bias))
                    or not np.all(np.isfinite(region_model.mean))
                    or not np.all(np.isfinite(region_model.scale))
                    or np.any(region_model.scale <= 0)
                    or not np.isfinite(region_model.distance_threshold)
                    or region_model.distance_threshold <= 0
                    or not np.isfinite(region_model.validation_error)
                    or region_model.validation_error < 0
                ):
                    raise ValueError("Artifact mô hình vùng chỉ số không hợp lệ.")
            model = cls(
                data["labels"].astype(np.int64),
                data["weights"].astype(np.float32),
                data["bias"].astype(np.float32),
                data["mean"].astype(np.float32),
                data["scale"].astype(np.float32),
                data["reading_lengths"].astype(np.int64)
                if "reading_lengths" in data.files
                else None,
                data["reading_length_counts"].astype(np.int64)
                if "reading_length_counts" in data.files
                else None,
                region_model,
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
        payload: dict[str, np.ndarray] = {
            "labels": self.labels,
            "weights": self.weights,
            "bias": self.bias,
            "mean": self.mean,
            "scale": self.scale,
        }
        if self.reading_lengths is not None:
            payload["reading_lengths"] = self.reading_lengths
        if self.reading_length_counts is not None:
            payload["reading_length_counts"] = self.reading_length_counts
        if self.region_model is not None:
            payload.update(
                {
                    "region_weights": self.region_model.weights,
                    "region_bias": self.region_model.bias,
                    "region_mean": self.region_model.mean,
                    "region_scale": self.region_model.scale,
                    "region_distance_threshold": np.array(
                        [self.region_model.distance_threshold], dtype=np.float32
                    ),
                    "region_validation_error": np.array(
                        [self.region_model.validation_error], dtype=np.float32
                    ),
                }
            )
        np.savez_compressed(path, **payload)

    def with_training_metadata(
        self,
        reading_lengths: list[int],
        region_model: ReadingRegionRegressor,
    ) -> "DigitHogSoftmaxModel":
        lengths, counts = np.unique(
            np.asarray(reading_lengths, dtype=np.int64), return_counts=True
        )
        return DigitHogSoftmaxModel(
            self.labels,
            self.weights,
            self.bias,
            self.mean,
            self.scale,
            lengths,
            counts,
            region_model,
        )

    def with_reading_lengths(
        self, reading_lengths: list[int]
    ) -> "DigitHogSoftmaxModel":
        lengths, counts = np.unique(
            np.asarray(reading_lengths, dtype=np.int64), return_counts=True
        )
        return DigitHogSoftmaxModel(
            self.labels,
            self.weights,
            self.bias,
            self.mean,
            self.scale,
            lengths,
            counts,
            None,
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

    def candidate_lengths(self) -> tuple[int, ...]:
        if self.reading_lengths is None or self.reading_length_counts is None:
            return (5, 6, 4, 7, 8)
        order = np.argsort(-self.reading_length_counts)
        return tuple(int(self.reading_lengths[index]) for index in order)

    def predict_region(
        self, image: np.ndarray
    ) -> tuple[tuple[tuple[float, float], ...], float] | None:
        return (
            self.region_model.predict(image) if self.region_model is not None else None
        )


def load_digit_model(path: Path) -> DigitModel:
    with np.load(path, allow_pickle=False) as data:
        keys = set(data.files)
    if {"weights", "bias", "mean", "scale"}.issubset(keys):
        return DigitHogSoftmaxModel.load(path)
    if "centroids" in keys:
        return DigitCentroidModel.load(path)
    raise ValueError("Không nhận diện được định dạng artifact mô hình chữ số.")
