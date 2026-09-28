import re
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from ai.pipeline.rapid import TextLine


class RegionPredictor(Protocol):
    def predict_region(
        self, image: np.ndarray
    ) -> tuple[tuple[tuple[float, float], ...], float] | None: ...


@dataclass(frozen=True)
class Detection:
    confidence: float
    meter_region: tuple[int, int, int, int] | None
    customer_region: tuple[int, int, int, int] | None
    reading_region: tuple[int, int, int, int] | None
    reading_polygon: tuple[tuple[float, float], ...] | None = None
    source: str = "HEURISTIC"


def _polygon_bbox(
    polygon: tuple[tuple[float, float], ...], width: int, height: int
) -> tuple[int, int, int, int]:
    left = max(0, round(min(point[0] for point in polygon) * width))
    top = max(0, round(min(point[1] for point in polygon) * height))
    right = min(width, round(max(point[0] for point in polygon) * width))
    bottom = min(height, round(max(point[1] for point in polygon) * height))
    return left, top, max(1, right - left), max(1, bottom - top)


def _ocr_reading_candidate(
    lines: list[TextLine], width: int, height: int
) -> tuple[tuple[int, int, int, int], float] | None:
    best: tuple[tuple[int, int, int, int], float] | None = None
    for line in lines:
        compact = re.sub(r"\s+", "", line.text)
        groups = re.findall(r"(?<!\d)\d{4,8}(?!\d)", compact)
        if not groups:
            continue
        left = max(0, int(min(point[0] for point in line.box)))
        top = max(0, int(min(point[1] for point in line.box)))
        right = min(width, int(max(point[0] for point in line.box)) + 1)
        bottom = min(height, int(max(point[1] for point in line.box)) + 1)
        box_width = max(1, right - left)
        box_height = max(1, bottom - top)
        aspect = box_width / box_height
        if aspect < 1.6:
            continue
        padding_x = round(box_width * 0.05)
        padding_y = round(box_height * 0.18)
        region = (
            max(0, left - padding_x),
            max(0, top - padding_y),
            min(width, right + padding_x) - max(0, left - padding_x),
            min(height, bottom + padding_y) - max(0, top - padding_y),
        )
        length_score = min(len(max(groups, key=len)) / 6, 1.0)
        score = min(0.88, line.confidence * 0.8 + length_score * 0.08)
        if best is None or score > best[1]:
            best = region, score
    return best


class MeterDetector:
    """Locate the reading register using learned corners, OCR evidence, then a safe fallback."""

    def __init__(self, region_predictor: RegionPredictor | None = None) -> None:
        self.region_predictor = region_predictor

    def detect(
        self, image: np.ndarray, lines: list[TextLine] | None = None
    ) -> Detection:
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
                best = score, (x, y, w, h)

        if best is None:
            meter = (0, int(height * 0.12), width, int(height * 0.78))
            meter_confidence = 0.3
        else:
            meter = best[1]
            meter_confidence = min(0.68, 0.45 + best[0] * 0.15)
        x, y, w, h = meter
        customer = (0, 0, width, min(height, y + int(h * 0.18)))

        learned = (
            self.region_predictor.predict_region(image)
            if self.region_predictor
            else None
        )
        if learned is not None:
            polygon, confidence = learned
            if confidence >= 0.55:
                return Detection(
                    confidence,
                    meter,
                    customer,
                    _polygon_bbox(polygon, width, height),
                    polygon,
                    "TRAINED_KEYPOINTS",
                )

        ocr_candidate = _ocr_reading_candidate(lines or [], width, height)
        if ocr_candidate is not None:
            reading, confidence = ocr_candidate
            return Detection(confidence, meter, customer, reading, None, "SCENE_OCR")

        reading = (
            x + int(w * 0.15),
            y + int(h * 0.22),
            max(1, int(w * 0.72)),
            max(1, int(h * 0.25)),
        )
        return Detection(
            round(meter_confidence, 4),
            meter,
            customer,
            reading,
            None,
            "HEURISTIC",
        )
