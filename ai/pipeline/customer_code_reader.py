import re
from subprocess import TimeoutExpired
from time import perf_counter

import numpy as np

from ai.pipeline.scene_ocr import TextLine, read_lines
from ai.pipeline.tesseract_cli import enhanced_variants, read


class CustomerCodeReader:
    pattern = re.compile(
        r"(?:MA\s*(?:KH|KHACH\s*HANG)|CUSTOMER)\s*[:\-]?\s*([A-Z0-9][A-Z0-9.\-]{2,})",
        re.IGNORECASE,
    )

    def read(
        self,
        image: np.ndarray,
        lines: list[TextLine] | None = None,
        *,
        fallback_budget_seconds: float = 8.0,
        diagnostics: dict | None = None,
    ) -> tuple[str | None, float]:
        diagnostics = diagnostics if diagnostics is not None else {}
        diagnostics.update(fallback_attempts=0, fallback_budget_exhausted=False)
        best: tuple[str | None, float] = (None, 0.0)
        for line in lines if lines is not None else read_lines(image):
            normalized = line.text.upper().replace("Á", "A").replace("Ã", "A")
            match = self.pattern.search(normalized)
            if match:
                value = self._normalize(match.group(1))
                if value and line.confidence > best[1]:
                    best = (value, round(line.confidence, 4))
        if best[0]:
            return best
        fallback_started = perf_counter()
        # Sparse-text mode is the best fit for labels; block mode is a bounded
        # fallback. PSM 12 duplicated PSM 11 work and added avoidable latency.
        for variant in enhanced_variants(image):
            for psm in (11, 6):
                remaining = fallback_budget_seconds - (
                    perf_counter() - fallback_started
                )
                if remaining <= 0:
                    diagnostics["fallback_budget_exhausted"] = True
                    return best
                diagnostics["fallback_attempts"] += 1
                try:
                    candidate = read(variant, psm=psm, timeout=min(20.0, remaining))
                except TimeoutExpired:
                    # Missing customer identity must be reviewable, not fail the job.
                    diagnostics["fallback_budget_exhausted"] = True
                    return best
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
                    if score >= 0.75:
                        return best
        return best

    @staticmethod
    def _normalize(value: str) -> str | None:
        normalized = re.sub(r"[^A-Z0-9.\-]", "", value.upper()).strip(".-")
        if normalized.startswith("KH"):
            normalized = "KH" + normalized[2:].translate(
                str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8"})
            )
        if len(re.sub(r"[^A-Z0-9]", "", normalized)) < 3:
            return None
        return normalized
