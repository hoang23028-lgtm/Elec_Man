import re

import cv2
import numpy as np

from ai.pipeline.rapid import TextLine, read_lines
from ai.pipeline.tesseract import enhanced_variants, read
from ai.training.digit_model import DigitModel, integer_register_strip, reading_features


class MeterReader:
    def __init__(self, trained_model: DigitModel | None = None) -> None:
        self.trained_model = trained_model

    def read(
        self,
        image: np.ndarray,
        lines: list[TextLine] | None = None,
        reading_bbox: tuple[float, float, float, float] | None = None,
    ) -> tuple[str | None, float]:
        integer_image = integer_register_strip(image)
        if integer_image.shape != image.shape:
            image = integer_image
            lines = read_lines(image)
        best: tuple[str | None, float] = (None, 0.0)
        for line in lines if lines is not None else read_lines(image):
            groups = self._integer_groups(line.text)
            for group in groups:
                box_height = max(point[1] for point in line.box) - min(
                    point[1] for point in line.box
                )
                score = min(
                    0.99,
                    line.confidence * 0.86
                    + min(box_height / max(image.shape[0] * 0.025, 1), 1) * 0.14,
                )
                if score > best[1]:
                    best = (group, round(score, 4))
        trained_best: tuple[str | None, float] = (None, 0.0)
        if self.trained_model is not None:
            lengths = list(self.trained_model.candidate_lengths())
            if best[0]:
                lengths.insert(0, len(best[0]))
            for digit_count in dict.fromkeys(lengths):
                if not 4 <= digit_count <= 8:
                    continue
                features = reading_features(
                    image,
                    digit_count,
                    self.trained_model.feature_mode,
                    reading_bbox,
                )
                trained_value, trained_confidence = self.trained_model.predict_features(
                    features
                )
                if trained_value and trained_confidence > trained_best[1]:
                    trained_best = trained_value, round(trained_confidence, 4)
            if trained_best[0] and trained_best[1] >= max(0.7, best[1]):
                return trained_best
        if best[0] and best[1] >= 0.72:
            return best

        variants = enhanced_variants(image)
        # Mechanical wheels are usually light digits on a dark strip, so test
        # both polarities. The red decimal wheel is intentionally ignored.
        variants.extend([cv2.bitwise_not(item) for item in variants])
        tesseract_candidates: dict[str, list[float]] = {}
        for variant in variants:
            for psm in (6, 7, 11, 13):
                candidate = read(variant, psm=psm, whitelist="0123456789.,")
                groups = self._integer_groups(candidate.text)
                for group in groups:
                    digits = len(group)
                    score = min(
                        0.94,
                        0.45 + candidate.confidence * 0.45 + min(digits, 6) * 0.015,
                    )
                    tesseract_candidates.setdefault(group, []).append(score)
        for group, scores in tesseract_candidates.items():
            consensus_bonus = min(0.09, max(0, len(scores) - 1) * 0.03)
            score = min(0.94, max(scores) + consensus_bonus)
            if score > best[1]:
                best = group, round(score, 4)
        return trained_best if trained_best[1] > best[1] else best

    @staticmethod
    def _integer_groups(text: str) -> list[str]:
        """Return only the main mechanical register, excluding decimal wheels."""
        return re.findall(r"\d{4,8}", text.replace(" ", ""))
