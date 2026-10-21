import re
import unicodedata
from math import isfinite
from subprocess import TimeoutExpired
from time import perf_counter

import numpy as np

from ai.pipeline.scene_ocr import TextLine, read_lines
from ai.pipeline.tesseract_cli import enhanced_variants, read


class CustomerCodeReader:
    pattern = re.compile(
        r"(?:MA\s*(?:KHACH\s*HANG|KH)|CUSTOMER)\s*[:\-]?\s*([A-Z0-9][A-Z0-9.\-]{2,})",
        re.IGNORECASE,
    )
    structured = re.compile(
        r"(?<![A-Z0-9.])([A-Z]{1,4}[0-9]{0,3}\s*\.\s*[0-9]{3,8})(?![A-Z0-9.])"
    )

    @classmethod
    def _candidates(cls, text):
        normalized = "".join(
            c
            for c in unicodedata.normalize("NFKD", text.upper())
            if not unicodedata.combining(c)
        )
        normalized = re.sub(r"\s*([.\-])\s*", r"\1", normalized)
        # No fuzzy match or guessed identifier: the server still reconciles the
        # extracted code with the customer master before any confirmation.
        standalone = [
            value
            for value in cls.structured.findall(normalized)
            if value.split(".")[0] not in {"NO", "REV", "CL", "PDM", "HZ", "SER"}
        ]
        matches = cls.pattern.findall(normalized) + standalone
        return {value for match in matches if (value := cls._normalize(match))}

    def read(
        self,
        image: np.ndarray,
        lines: list[TextLine] | None = None,
        *,
        fallback_budget_seconds: float = 3.0,
        diagnostics: dict | None = None,
    ) -> tuple[str | None, float]:
        diagnostics = diagnostics if diagnostics is not None else {}
        diagnostics.update(
            fallback_attempts=0,
            fallback_budget_exhausted=False,
            reused_scene_lines=lines is not None,
        )
        if (
            not isfinite(fallback_budget_seconds)
            or not 0 <= fallback_budget_seconds <= 8
        ):
            raise ValueError("Ngân sách OCR khách hàng phải từ 0 đến 8 giây.")
        found = {}
        for line in lines if lines is not None else read_lines(image):
            if not isfinite(line.confidence) or not 0 <= line.confidence <= 1:
                continue
            for value in self._candidates(line.text):
                found[value] = max(found.get(value, 0), min(0.899, line.confidence))
        if found:
            diagnostics["decision"] = (
                ("scene_match" if lines is not None else "crop_match")
                if len(found) == 1
                else "ambiguous_codes"
            )
            return (
                (next(iter(found)), round(next(iter(found.values())), 4))
                if len(found) == 1
                else (None, 0.0)
            )
        best: tuple[str | None, float] = (None, 0.0)
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
                    candidate = read(variant, psm=psm, timeout=remaining)
                except TimeoutExpired:
                    # Missing customer identity must be reviewable, not fail the job.
                    diagnostics["fallback_budget_exhausted"] = True
                    return best
                values = self._candidates(candidate.text)
                if len(values) > 1:
                    diagnostics["decision"] = "ambiguous_codes"
                    return None, 0.0
                if (
                    not values
                    or not isfinite(candidate.confidence)
                    or not 0 <= candidate.confidence <= 1
                ):
                    continue
                value = next(iter(values))
                if best[0] is not None and best[0] != value:
                    diagnostics["decision"] = "ambiguous_codes"
                    return None, 0.0
                score = min(0.899, 0.55 + candidate.confidence * 0.4)
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
