from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    confidence: float
    meter_region: tuple[int, int, int, int] | None
    customer_region: tuple[int, int, int, int] | None
    reading_region: tuple[int, int, int, int] | None


class MeterDetector:
    """Find the meter window and derive OCR regions without a trained detector."""

    def detect(self, image: np.ndarray) -> Detection:
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 45, 135)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        best: tuple[float, tuple[int, int, int, int]] | None = None
        image_area = float(width * height)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area_ratio = (w * h) / image_area
            aspect = w / max(h, 1)
            if not 0.06 <= area_ratio <= 0.75 or not 0.65 <= aspect <= 2.2:
                continue
            center_x = (x + w / 2) / width
            center_y = (y + h / 2) / height
            center_score = max(0.0, 1.0 - abs(center_x - 0.5) - abs(center_y - 0.48))
            score = area_ratio * 2.0 + center_score
            if best is None or score > best[0]:
                best = (score, (x, y, w, h))

        if best is None:
            meter = (0, int(height * 0.12), width, int(height * 0.78))
            confidence = 0.35
        else:
            meter = best[1]
            confidence = min(0.92, 0.55 + best[0] * 0.2)

        x, y, w, h = meter
        customer = (0, 0, width, min(height, y + int(h * 0.18)))
        reading = (
            x + int(w * 0.15),
            y + int(h * 0.22),
            max(1, int(w * 0.72)),
            max(1, int(h * 0.25)),
        )
        return Detection(round(confidence, 4), meter, customer, reading)
