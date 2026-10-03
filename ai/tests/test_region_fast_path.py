import json
from subprocess import TimeoutExpired
from unittest.mock import Mock

import cv2
import numpy as np

from ai.pipeline import customer_code_reader as customer_module
from ai.pipeline import meter_pipeline as pipeline_module
from ai.readers.consensus import ConsensusMeterReader


def test_manual_region_skips_full_image_recognition(tmp_path, monkeypatch):
    path = tmp_path / "meter.png"
    cv2.imwrite(str(path), np.full((200, 300, 3), 128, dtype=np.uint8))
    pipeline = pipeline_module.MeterReadingPipeline()
    forbidden = Mock(
        side_effect=AssertionError("full image processing must be skipped")
    )
    monkeypatch.setattr(pipeline_module, "read_lines", forbidden)
    monkeypatch.setattr(pipeline.customer_code_reader, "read", forbidden)
    monkeypatch.setattr(pipeline.meter_locator, "locate", forbidden)
    monkeypatch.setattr(pipeline.reading_region_locator, "locate", forbidden)
    read = Mock(return_value=("01234", 0.89))
    monkeypatch.setattr(pipeline.meter_reader, "read", read)

    result = pipeline.process(path, reading_bbox=(0.2, 0.3, 0.6, 0.2))

    assert result["reading_only"] is True
    assert result["meter_reading_ai"] == "01234"
    assert result["human_region_requested"] is True
    assert "read_digits" in result["timings_ms"]
    assert read.call_args.kwargs["integer_digits"] == 5
    assert read.call_args.args[0].shape[0] < 200
    forbidden.assert_not_called()


def test_remote_reader_returns_consensus(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        @staticmethod
        def read():
            return json.dumps(
                {
                    "value": "12345",
                    "confidence": 0.89,
                    "diagnostics": {"decision": "agreement"},
                }
            ).encode()

    monkeypatch.setattr("ai.readers.consensus.urlopen", lambda *_, **__: Response())
    stats = {}

    value, confidence = ConsensusMeterReader(
        "http://ppocr", "http://parseq", timeout=1
    ).read(
        np.full((30, 180, 3), 128, dtype=np.uint8),
        integer_digits=5,
        diagnostics=stats,
    )

    assert (value, confidence) == ("12345", 0.878)
    assert stats["decision"] == "agreement"


def test_customer_timeout_is_reviewable_and_never_retried(monkeypatch):
    read = Mock(side_effect=TimeoutExpired("tesseract", 0.1))
    monkeypatch.setattr(customer_module, "read", read)
    stats = {}
    assert customer_module.CustomerCodeReader().read(
        np.full((30, 180, 3), 128, dtype=np.uint8), [], diagnostics=stats
    ) == (None, 0.0)
    read.assert_called_once()
    assert 0 < read.call_args.kwargs["timeout"] <= 8
    assert stats["fallback_budget_exhausted"] is True
