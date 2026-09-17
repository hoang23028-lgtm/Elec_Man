import cv2
import numpy as np


def prepare_for_detection(image: np.ndarray) -> np.ndarray:
    """Apply only conservative normalization; original files are never changed."""
    height, width = image.shape[:2]
    if max(height, width) > 1600:
        scale = 1600 / max(height, width)
        return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    return image.copy()
