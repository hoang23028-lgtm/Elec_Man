from pathlib import Path
from time import perf_counter

import cv2

from ai.pipeline.confidence import calculate
from ai.pipeline.customer_ocr import CustomerOcr
from ai.pipeline.detector import MeterDetector
from ai.pipeline.meter_reader import MeterReader
from ai.pipeline.preprocessing import prepare_for_detection
from ai.pipeline.quality import assess_image_quality
from ai.pipeline.rapid import read_lines
from ai.pipeline.validator import validate
from ai.training.digit_model import load_digit_model


class DevelopmentPipeline:
    """Pretrained OCR baseline for bootstrapping a human-reviewed dataset."""

    name = "OCR_BASELINE"

    def __init__(
        self, digit_model_path: Path | None = None, model_version: str | None = None
    ) -> None:
        self.name = (
            "SPECIALIZED_METER_DIGIT_MODEL" if digit_model_path else "OCR_BASELINE"
        )
        self.model_version = model_version or "meter-ocr-baseline-v2-integer"
        self.detector = MeterDetector()
        self.customer_ocr = CustomerOcr()
        trained_model = load_digit_model(digit_model_path) if digit_model_path else None
        self.meter_reader = MeterReader(trained_model)

    def process(
        self,
        image_path: Path,
        reading_bbox: tuple[float, float, float, float] | None = None,
    ) -> dict:
        started = perf_counter()
        source = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if source is None:
            raise ValueError("OpenCV không thể giải mã hình ảnh.")
        quality = assess_image_quality(source)
        prepared = prepare_for_detection(source)
        detection = self.detector.detect(prepared)

        lines = read_lines(prepared)
        customer_id, customer_confidence = self.customer_ocr.read(prepared, lines)
        human_reading_region = None
        if reading_bbox is not None:
            image_height, image_width = prepared.shape[:2]
            normalized_x, normalized_y, normalized_width, normalized_height = (
                reading_bbox
            )
            x = max(0, min(image_width - 1, round(normalized_x * image_width)))
            y = max(0, min(image_height - 1, round(normalized_y * image_height)))
            right = max(
                x + 1,
                min(
                    image_width, round((normalized_x + normalized_width) * image_width)
                ),
            )
            bottom = max(
                y + 1,
                min(
                    image_height,
                    round((normalized_y + normalized_height) * image_height),
                ),
            )
            human_reading_region = (x, y, right - x, bottom - y)
            reading_crop = prepared[y:bottom, x:right]
            crop_lines = read_lines(reading_crop)
            meter_reading, meter_confidence = self.meter_reader.read(
                reading_crop,
                crop_lines,
                (0.0, 0.0, 1.0, 1.0),
            )
        else:
            meter_reading, meter_confidence = self.meter_reader.read(prepared, lines)
        validation = validate(customer_id, meter_reading)
        final_confidence = calculate(
            customer_confidence,
            meter_confidence,
            1.0 if reading_bbox is not None else detection.confidence,
            quality["quality_score"],
            validation["valid"],
        )
        return {
            "processor": self.name,
            "is_mock": False,
            "model_version": self.model_version,
            "customer_id_ai": customer_id,
            "meter_reading_ai": meter_reading,
            "customer_confidence": customer_confidence,
            "meter_confidence": meter_confidence,
            "detection_confidence": 1.0
            if reading_bbox is not None
            else detection.confidence,
            "image_quality_score": quality["quality_score"],
            "final_confidence": final_confidence,
            "status": "REVIEW",
            "human_region_requested": reading_bbox is not None,
            "quality": quality,
            "validation": validation,
            "ocr_lines": len(lines),
            "regions": {
                "meter": detection.meter_region,
                "customer": detection.customer_region,
                "reading": detection.reading_region,
                "human_reading": human_reading_region,
            },
            "processing_time_ms": round((perf_counter() - started) * 1000),
        }
