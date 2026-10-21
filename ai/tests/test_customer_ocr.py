from threading import Event
from unittest.mock import Mock

import cv2
import numpy as np
import pytest

from ai.pipeline import customer_code_reader as module
from ai.pipeline import meter_pipeline
from ai.pipeline.scene_ocr import TextLine
from ai.pipeline.tesseract_cli import OcrCandidate, enhanced_variants


def test_preprocessing_only_builds_the_two_variants_actually_consumed(monkeypatch):
    monkeypatch.setattr(
        cv2,
        "adaptiveThreshold",
        Mock(side_effect=AssertionError("Unused third variant must not be computed")),
    )
    variants = enhanced_variants(np.full((40, 200, 3), 128, np.uint8))
    assert len(variants) == 2
    assert all(image.ndim == 2 and image.dtype == np.uint8 for image in variants)


@pytest.mark.parametrize(
    "text",
    ["PN2.001", "Mã KH: PN2.001", "mã khách hàng: PN2 . 001", "CUSTOMER: PN2.001"],
)
def test_reuses_scene_code_without_tesseract_and_preserves_prefix(text, monkeypatch):
    fallback = Mock(side_effect=AssertionError("Must reuse scene OCR"))
    monkeypatch.setattr(module, "read", fallback)
    stats = {}
    assert module.CustomerCodeReader().read(
        np.zeros((40, 200, 3), np.uint8), [TextLine((), text, 0.98)], diagnostics=stats
    ) == ("PN2.001", 0.899)
    assert stats["fallback_attempts"] == 0
    assert stats["decision"] == "scene_match"


def test_ambiguous_scene_codes_abstain_instead_of_selecting_highest_score(monkeypatch):
    monkeypatch.setattr(module, "read", Mock(side_effect=AssertionError("No fallback")))
    stats = {}
    result = module.CustomerCodeReader().read(
        np.zeros((40, 200, 3), np.uint8),
        [TextLine((), "PN2.001", 0.99), TextLine((), "PN2.002", 0.6)],
        diagnostics=stats,
    )
    assert result == (None, 0)
    assert stats["decision"] == "ambiguous_codes"


@pytest.mark.parametrize("code", ["PN.001", "UB.001"])
def test_standalone_codes_with_letter_only_prefix_remain_supported(code):
    value, score = module.CustomerCodeReader().read(
        np.zeros((40, 200, 3), np.uint8), [TextLine((), code, 0.9)]
    )
    assert value == code and score <= 0.899


def test_customer_fallback_is_bounded_to_four_attempts_and_three_seconds(monkeypatch):
    fallback = Mock(return_value=OcrCandidate("230V 50Hz No.2011 900 rev/kWh", 0.99))
    monkeypatch.setattr(module, "read", fallback)
    stats = {}
    assert module.CustomerCodeReader().read(
        np.zeros((40, 200, 3), np.uint8), [], diagnostics=stats
    ) == (None, 0)
    assert fallback.call_count == stats["fallback_attempts"] == 4
    assert all(0 < c.kwargs["timeout"] <= 3 for c in fallback.call_args_list)


@pytest.mark.parametrize("budget", [-1, 9, float("inf"), float("nan")])
def test_customer_budget_must_be_finite_and_bounded(budget):
    with pytest.raises(ValueError):
        module.CustomerCodeReader().read(
            np.zeros((40, 200, 3), np.uint8), [], fallback_budget_seconds=budget
        )


@pytest.mark.parametrize("trained", [False, True])
def test_digits_run_while_customer_ocr_is_pending_and_both_are_joined(
    tmp_path, monkeypatch, trained
):
    path = tmp_path / "meter.png"
    cv2.imwrite(str(path), np.full((200, 300, 3), 128, np.uint8))
    pipeline = meter_pipeline.MeterReadingPipeline()
    customer_started, digits_ready = Event(), Event()
    monkeypatch.setattr(meter_pipeline, "read_lines", lambda _: [])

    if trained:
        from ai.pipeline.localization import ReadingRegionLocation

        monkeypatch.setattr(
            pipeline.reading_region_locator,
            "locate",
            lambda *a, **kw: ReadingRegionLocation(
                0.8, (50, 50, 180, 40), None, "TRAINED_KEYPOINTS"
            ),
        )

    def customer(_, lines, **__):
        assert lines is None if trained else lines == []
        customer_started.set()
        assert digits_ready.wait(3), "Digit OCR was blocked behind customer OCR"
        return "PN2.001", 0.8

    def digits(*_, **__):
        assert customer_started.wait(3)
        digits_ready.set()
        return "01234", 0.8

    monkeypatch.setattr(pipeline.customer_code_reader, "read", customer)
    monkeypatch.setattr(pipeline.meter_reader, "read", digits)
    try:
        result = pipeline.process(path)
    finally:
        pipeline.meter_reader.close()
    assert result["customer_id_ai"] == "PN2.001"
    assert result["meter_reading_ai"] == "01234"
    assert result["status"] == "REVIEW"
    assert result["timings_ms"]["customer_wait"] >= 0
    assert result["reader_diagnostics"]["digits_ready_ms"] >= 0


def test_scene_engine_bounds_both_ort_thread_pools(monkeypatch):
    from ai.pipeline import scene_ocr

    factory = Mock(return_value=lambda _: ([], None))
    monkeypatch.setattr(scene_ocr, "_engine", None)
    monkeypatch.setattr(scene_ocr, "RapidOCR", factory)
    assert scene_ocr.read_lines(np.zeros((40, 200, 3), np.uint8)) == []
    factory.assert_called_once_with(intra_op_num_threads=1, inter_op_num_threads=1)
