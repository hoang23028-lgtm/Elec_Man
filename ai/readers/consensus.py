"""Parallel consensus client for isolated sequence-reader services."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cv2
import numpy as np

from app.core.config import get_settings


class ConsensusMeterReader:
    name = "ppocr-v6-small-parseq-tiny-consensus-v1"

    def __init__(
        self,
        ppocr_endpoint: str | None = None,
        parseq_endpoint: str | None = None,
        timeout: float | None = None,
    ) -> None:
        settings = get_settings()
        self.endpoints = {
            "ppocr": (ppocr_endpoint or settings.ppocr_reader_url).rstrip("/"),
            "parseq": (parseq_endpoint or settings.parseq_reader_url).rstrip("/"),
        }
        self.timeout = timeout or settings.sequence_reader_timeout_seconds
        self._executor = ThreadPoolExecutor(
            max_workers=len(self.endpoints),
            thread_name_prefix="meter-reader",
        )

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _request(self, endpoint: str, body: bytes) -> tuple[str | None, float]:
        request = Request(
            f"{endpoint}/v1/read",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read())
        value = result.get("value")
        return (str(value) if value is not None else None), float(
            result.get("confidence") or 0.0
        )

    def read(
        self,
        image: np.ndarray,
        *,
        diagnostics: dict | None = None,
        integer_digits: int | None = None,
    ) -> tuple[str | None, float]:
        stats = diagnostics if diagnostics is not None else {}
        stats["reader"] = self.name
        if integer_digits is None:
            stats["decision"] = "missing_integer_digit_count"
            return None, 0.0
        if integer_digits not in range(4, 9):
            raise ValueError("Số chữ số nguyên phải từ 4 đến 8.")
        # Register cleanup belongs to each inference service. Encoding the crop
        # here avoids duplicate preprocessing and keeps both readers consistent.
        encoded, payload = cv2.imencode(".png", image)
        if not encoded:
            stats["decision"] = "image_encode_failed"
            return None, 0.0
        body = json.dumps(
            {
                "image_base64": base64.b64encode(payload).decode("ascii"),
                "integer_digits": integer_digits,
            }
        ).encode("utf-8")
        candidates = {}
        try:
            futures = {
                backend: self._executor.submit(self._request, endpoint, body)
                for backend, endpoint in self.endpoints.items()
            }
            for backend, future in futures.items():
                value, score = future.result()
                candidates[backend] = {
                    "value": value,
                    "score_uncalibrated": round(score, 6),
                }
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            stats.update(candidates=candidates, decision="reader_service_unavailable")
            return None, 0.0
        stats["candidates"] = candidates
        ppocr = candidates["ppocr"]
        parseq = candidates["parseq"]
        if ppocr["value"] is None or ppocr["value"] != parseq["value"]:
            stats["decision"] = "needs_human_review"
            return None, 0.0
        raw_score = min(ppocr["score_uncalibrated"], parseq["score_uncalibrated"])
        confidence = round(min(0.899, 0.7 + 0.2 * raw_score), 4)
        stats["decision"] = "agreement"
        return ppocr["value"], confidence
