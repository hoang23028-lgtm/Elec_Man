import re

import numpy as np

from ai.pipeline.rapid import TextLine, read_lines
from ai.pipeline.tesseract import enhanced_variants, read


class CustomerOcr:
    pattern = re.compile(r"(?:MA\s*KH|KH)\s*[:\-]?\s*(K?H?[A-Z0-9]{2,})", re.IGNORECASE)

    def read(self, image: np.ndarray, lines: list[TextLine] | None = None) -> tuple[str | None, float]:
        best: tuple[str | None, float] = (None, 0.0)
        for line in lines if lines is not None else read_lines(image):
            normalized = re.sub(r"[^A-Z0-9]", "", line.text.upper())
            match = re.search(r"(?:MAKH)?(KH[A-Z0-9]{2,})", normalized)
            if match:
                value = self._normalize(match.group(1))
                if value and line.confidence > best[1]:
                    best = (value, round(line.confidence, 4))
        if best[0]:
            return best
        for variant in enhanced_variants(image):
            for psm in (6, 11, 12):
                candidate = read(variant, psm=psm)
                normalized = candidate.text.upper().replace("Á", "A").replace("Ã", "A")
                match = self.pattern.search(normalized)
                if not match:
                    continue
                value = self._normalize(match.group(1).replace(" ", ""))
                if not value:
                    continue
                score = min(0.95, 0.55 + candidate.confidence * 0.4)
                if score > best[1]:
                    best = (value, round(score, 4))
        return best

    @staticmethod
    def _normalize(value: str) -> str | None:
        if not value.startswith("KH"):
            value = f"KH{value.lstrip('KH')}"
        tail = value[2:].translate(str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8"}))
        return f"KH{tail}" if len(tail) >= 2 else None
