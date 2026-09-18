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
        best_line: TextLine | None = None
        for line in lines if lines is not None else read_lines(image):
            groups = re.findall(r"\d{4,7}", line.text.replace(" ", ""))
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
                    best_line = line
        if best_line and best[0]:
            decimal, decimal_confidence = self._read_decimal_wheel(
                image, best_line, len(best[0])
            )
            if decimal:
                return f"{best[0]}.{decimal}", round(
                    min(best[1], decimal_confidence), 4
                )
            return best

        variants = enhanced_variants(image)
        # Mechanical wheels are usually light digits on a dark strip; include
        # both polarities because red decimal wheels vary between meter types.
        variants.extend([cv2.bitwise_not(item) for item in variants])
        for variant in variants:
            for psm in (6, 7, 11, 13):
                candidate = read(variant, psm=psm, whitelist="0123456789.,")
                groups = re.findall(
                    r"\d{4,7}(?:[.,]\d)?", candidate.text.replace(" ", "")
                )
                for group in groups:
                    value = group.replace(",", ".")
                    digits = len(value.replace(".", ""))
                    if not 4 <= digits <= 7:
                        continue
                    score = min(
                        0.94,
                        0.45 + candidate.confidence * 0.45 + min(digits, 6) * 0.015,
                    )
                    if score > best[1]:
                        best = (value, round(score, 4))
        return best

    @staticmethod
    def _read_decimal_wheel(
        image: np.ndarray, line: TextLine, digit_count: int
    ) -> tuple[str | None, float]:
        left = min(point[0] for point in line.box)
        right = max(point[0] for point in line.box)
        top = min(point[1] for point in line.box)
        bottom = max(point[1] for point in line.box)
        digit_width = max((right - left) / max(digit_count, 1), 4)
        line_height = max(bottom - top, 4)
        x1 = max(0, round(right + digit_width * 0.25))
        x2 = min(image.shape[1], round(right + digit_width * 1.95))
        y1 = max(0, round(top - line_height * 0.48))
        y2 = min(image.shape[0], round(bottom + line_height * 0.45))
        wheel = image[y1:y2, x1:x2]
        best: tuple[str | None, float] = (None, 0.0)
        for variant in enhanced_variants(wheel):
            for psm in (10, 13):
                candidate = read(variant, psm=psm, whitelist="0123456789")
                match = re.search(r"\d", candidate.text)
                if match and candidate.confidence > best[1]:
                    best = (match.group(0), candidate.confidence)
        return best
