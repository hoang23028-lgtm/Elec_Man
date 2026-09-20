import re

import cv2
import numpy as np

from ai.pipeline.rapid import TextLine, read_lines
from ai.pipeline.tesseract import enhanced_variants, read


class MeterReader:
    def read(
        self, image: np.ndarray, lines: list[TextLine] | None = None
    ) -> tuple[str | None, float]:
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
        if best[0]:
            return best

        variants = enhanced_variants(image)
        # Mechanical wheels are usually light digits on a dark strip, so test
        # both polarities. The red decimal wheel is intentionally ignored.
        variants.extend([cv2.bitwise_not(item) for item in variants])
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
                    if score > best[1]:
                        best = (group, round(score, 4))
        return best

    @staticmethod
    def _integer_groups(text: str) -> list[str]:
        """Return only the main mechanical register, excluding decimal wheels."""
        return re.findall(r"\d{4,8}", text.replace(" ", ""))
