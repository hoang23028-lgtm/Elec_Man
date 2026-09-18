import cv2
import numpy as np


def assess_image_quality(image: np.ndarray) -> dict:
    """Calculate quality metrics from an already-decoded image."""
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(grayscale, cv2.CV_64F).var())
    brightness = float(np.mean(grayscale))
    contrast = float(np.std(grayscale))
    height, width = grayscale.shape
    warnings: list[str] = []
    if width < 640 or height < 480:
        warnings.append("low_resolution")
    if blur_score < 50:
        warnings.append("possibly_blurry")
    if brightness < 35:
        warnings.append("underexposed")
    if brightness > 225:
        warnings.append("overexposed")
    score = min(
        1.0,
        (min(blur_score, 250) / 250) * 0.4
        + (1 - min(abs(brightness - 128) / 128, 1)) * 0.3
        + min(contrast / 64, 1) * 0.3,
    )
    return {
        "blur_score": round(blur_score, 2),
        "brightness_score": round(brightness, 2),
        "contrast_score": round(contrast, 2),
        "resolution_ok": width >= 640 and height >= 480,
        "quality_score": round(score, 4),
        "warnings": warnings,
    }
