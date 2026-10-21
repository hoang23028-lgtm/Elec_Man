from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


def extract_region_features(image: np.ndarray) -> np.ndarray:
    """Compact appearance features for supervised four-corner regression."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    resized = cv2.resize(gray, (24, 24), interpolation=cv2.INTER_AREA)
    normalized = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(resized)
    gradient_x = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(gradient_x, gradient_y)
    if magnitude.max() > 0:
        magnitude /= magnitude.max()
    intensity = normalized.astype(np.float32) / 255.0
    return np.concatenate((intensity.reshape(-1), magnitude.reshape(-1)))


def _signed_area(points: np.ndarray) -> float:
    shifted = np.roll(points, -1, axis=0)
    return float(
        np.sum(points[:, 0] * shifted[:, 1] - points[:, 1] * shifted[:, 0]) / 2
    )


def order_polygon(points: np.ndarray) -> np.ndarray:
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    ordered = points[np.argsort(angles)]
    first = int(np.argmin(ordered.sum(axis=1)))
    ordered = np.concatenate((ordered[first:], ordered[:first]))
    if _signed_area(ordered) < 0:
        ordered = ordered[[0, 3, 2, 1]]
    return ordered


def valid_polygon(points: np.ndarray) -> bool:
    if points.shape != (4, 2) or not np.all(np.isfinite(points)):
        return False
    turns = []
    for index in range(4):
        left = points[(index + 1) % 4] - points[index]
        right = points[(index + 2) % 4] - points[(index + 1) % 4]
        turns.append(float(left[0] * right[1] - left[1] * right[0]))
    return abs(_signed_area(points)) >= 0.000025 and (
        all(turn > 0 for turn in turns) or all(turn < 0 for turn in turns)
    )


@dataclass(frozen=True)
class KeypointRegionRegressor:
    weights: np.ndarray
    bias: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    distance_threshold: float
    validation_error: float = 1.0
    coordinate_space: str = "image"

    @classmethod
    def load(cls, path: Path) -> "KeypointRegionRegressor":
        with np.load(path, allow_pickle=False) as data:
            model = cls(
                data["weights"].astype(np.float32),
                data["bias"].astype(np.float32),
                data["mean"].astype(np.float32),
                data["scale"].astype(np.float32),
                float(data["distance_threshold"][0]),
                float(data["validation_error"][0]),
                str(data["coordinate_space"][0])
                if "coordinate_space" in data
                else "image",
            )
        if (
            model.weights.ndim != 2
            or model.weights.shape != (model.mean.size, 8)
            or model.bias.shape != (8,)
            or model.mean.ndim != 1
            or model.scale.shape != model.mean.shape
            or not np.all(np.isfinite(model.weights))
            or not np.all(np.isfinite(model.bias))
            or not np.all(np.isfinite(model.mean))
            or not np.all(np.isfinite(model.scale))
            or np.any(model.scale <= 0)
            or not np.isfinite(model.distance_threshold)
            or model.distance_threshold <= 0
            or not np.isfinite(model.validation_error)
            or model.validation_error < 0
            or model.coordinate_space not in {"image", "meter"}
        ):
            raise ValueError("Artifact mô hình vùng chỉ số không hợp lệ.")
        return model

    def save(self, path: Path) -> None:
        np.savez_compressed(
            path,
            weights=self.weights,
            bias=self.bias,
            mean=self.mean,
            scale=self.scale,
            distance_threshold=np.array([self.distance_threshold], dtype=np.float32),
            validation_error=np.array([self.validation_error], dtype=np.float32),
            coordinate_space=np.array([self.coordinate_space]),
        )

    @classmethod
    def train(
        cls,
        features: list[np.ndarray],
        targets: list[np.ndarray],
        *,
        regularization: float = 2.0,
    ) -> "KeypointRegionRegressor":
        if len(features) < 2 or len(features) != len(targets):
            raise ValueError("Dữ liệu vùng chỉ số không đủ để huấn luyện.")
        if not np.isfinite(regularization) or regularization <= 0:
            raise ValueError("Hệ số regularization phải hữu hạn và dương.")
        matrix = np.stack(features).astype(np.float32)
        target_matrix = np.stack(targets).astype(np.float32).reshape(-1, 8)
        mean = matrix.mean(axis=0)
        scale = matrix.std(axis=0)
        scale[scale < 1e-5] = 1.0
        normalized = (matrix - mean) / scale
        bias = target_matrix.mean(axis=0)
        centered_targets = target_matrix - bias
        if (
            matrix.ndim != 2
            or not np.isfinite(matrix).all()
            or not np.isfinite(target_matrix).all()
        ):
            raise ValueError("Đặc trưng/nhãn định vị không hợp lệ.")
        # Solve the smaller system: memory O(min(samples, features)^2).
        if normalized.shape[0] <= normalized.shape[1]:
            kernel = normalized @ normalized.T
            kernel.flat[:: kernel.shape[0] + 1] += regularization
            weights = normalized.T @ np.linalg.solve(kernel, centered_targets)
        else:
            kernel = normalized.T @ normalized
            kernel.flat[:: kernel.shape[0] + 1] += regularization
            weights = np.linalg.solve(kernel, normalized.T @ centered_targets)
        distances = np.linalg.norm(normalized, axis=1) / np.sqrt(normalized.shape[1])
        threshold = max(0.25, float(np.quantile(distances, 0.95)))
        return cls(
            weights.astype(np.float32),
            bias.astype(np.float32),
            mean,
            scale,
            threshold,
        )

    def with_validation_error(self, error: float) -> "KeypointRegionRegressor":
        return KeypointRegionRegressor(
            self.weights,
            self.bias,
            self.mean,
            self.scale,
            self.distance_threshold,
            max(0.0, float(error)),
            self.coordinate_space,
        )

    def in_meter_coordinates(self):
        from dataclasses import replace

        return replace(self, coordinate_space="meter")

    def predict_region(
        self, image: np.ndarray
    ) -> tuple[tuple[tuple[float, float], ...], float] | None:
        """Implement the shared runtime region-predictor contract."""
        return self.predict(image)

    def predict(
        self, image: np.ndarray
    ) -> tuple[tuple[tuple[float, float], ...], float] | None:
        feature = extract_region_features(image)
        if feature.shape != self.mean.shape:
            return None
        normalized = (feature - self.mean) / self.scale
        points = np.clip(
            (normalized @ self.weights + self.bias).reshape(4, 2), 0.0, 1.0
        )
        points = order_polygon(points)
        if not valid_polygon(points):
            return None
        distance = float(np.linalg.norm(normalized) / np.sqrt(normalized.size))
        similarity = min(1.0, self.distance_threshold / max(distance, 1e-6))
        confidence = min(0.95, max(0.0, 1.0 - self.validation_error * 4.0) * similarity)
        polygon = tuple((float(point[0]), float(point[1])) for point in points)
        return polygon, round(confidence, 4)
