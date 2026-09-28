from pathlib import Path
from time import perf_counter

import cv2

from ai.pipeline.confidence import calculate
from ai.pipeline.customer_ocr import CustomerOcr
from ai.pipeline.detector import MeterDetector
from ai.pipeline.geometry import normalized_bbox_polygon, perspective_crop
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
        self.customer_ocr = CustomerOcr()
        trained_model = load_digit_model(digit_model_path) if digit_model_path else None
        self.detector = MeterDetector(trained_model)
        self.meter_reader = MeterReader(trained_model)

    def process(
        self,
        image_path: Path,
        reading_bbox: tuple[float, float, float, float] | None = None,
        reading_polygon: tuple[tuple[float, float], ...] | None = None,
    ) -> dict:
        started = perf_counter()
        source = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if source is None:
            raise ValueError("OpenCV không thể giải mã hình ảnh.")
        quality = assess_image_quality(source)
        prepared = prepare_for_detection(source)
        lines = read_lines(prepared)
        detection = self.detector.detect(prepared, lines)
        customer_id, customer_confidence = self.customer_ocr.read(prepared, lines)
        human_reading_region = None
        selected_polygon = reading_polygon or (
            normalized_bbox_polygon(reading_bbox) if reading_bbox is not None else None
        )
        if selected_polygon is not None:
            image_height, image_width = prepared.shape[:2]
            human_reading_region = [
                [round(x * image_width), round(y * image_height)]
                for x, y in selected_polygon
            ]
            reading_crop = perspective_crop(prepared, selected_polygon)
            crop_lines = read_lines(reading_crop)
            meter_reading, meter_confidence = self.meter_reader.read(
                reading_crop,
                crop_lines,
                (0.0, 0.0, 1.0, 1.0),
            )
        elif detection.reading_polygon is not None:
            reading_crop = perspective_crop(prepared, detection.reading_polygon)
            crop_lines = read_lines(reading_crop)
            meter_reading, meter_confidence = self.meter_reader.read(
                reading_crop,
                crop_lines,
                (0.0, 0.0, 1.0, 1.0),
            )
        elif detection.reading_region is not None:
            x, y, width, height = detection.reading_region
            reading_crop = prepared[y : y + height, x : x + width]
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
            1.0 if selected_polygon is not None else detection.confidence,
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
            if selected_polygon is not None
            else detection.confidence,
            "image_quality_score": quality["quality_score"],
            "final_confidence": final_confidence,
            "status": "REVIEW",
            "human_region_requested": selected_polygon is not None,
            "detection_source": "HUMAN_REVIEW"
            if selected_polygon is not None
            else detection.source,
            "quality": quality,
            "validation": validation,
            "ocr_lines": len(lines),
            "regions": {
                "meter": detection.meter_region,
                "customer": detection.customer_region,
                "reading": detection.reading_region,
                "reading_polygon": detection.reading_polygon,
                "human_reading": human_reading_region,
            },
            "processing_time_ms": round((perf_counter() - started) * 1000),
        }
