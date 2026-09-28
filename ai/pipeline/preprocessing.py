import cv2
import numpy as np


class ImagePreprocessingModel:
    """Stage 1: conservative image enhancement with stable geometry."""

    name = "adaptive-image-preprocessor"
    version = "baseline-v1"

    def process(self, image: np.ndarray) -> tuple[np.ndarray, float, tuple[str, ...]]:
        prepared = prepare_for_detection(image)
        gray = cv2.cvtColor(prepared, cv2.COLOR_BGR2GRAY)
        brightness = float(gray.mean())
        contrast = float(gray.std())
        operations: list[str] = ["resize"] if prepared.shape != image.shape else []
        if contrast < 35 or brightness < 65 or brightness > 205:
            lab = cv2.cvtColor(prepared, cv2.COLOR_BGR2LAB)
            lightness, channel_a, channel_b = cv2.split(lab)
            lightness = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8)).apply(
                lightness
            )
            prepared = cv2.cvtColor(
                cv2.merge((lightness, channel_a, channel_b)), cv2.COLOR_LAB2BGR
            )
            operations.append("adaptive_contrast")
        confidence = min(0.82, max(0.45, 0.55 + min(contrast / 255, 0.27)))
        return prepared, round(confidence, 4), tuple(operations or ["identity"])


def prepare_for_detection(image: np.ndarray) -> np.ndarray:
    """Apply only conservative normalization; original files are never changed."""
    height, width = image.shape[:2]
    if max(height, width) > 1600:
        scale = 1600 / max(height, width)
        return cv2.resize(
            image,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
    return image.copy()
