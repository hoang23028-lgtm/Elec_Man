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


class DevelopmentPipeline:
    """Pretrained OCR baseline for bootstrapping a human-reviewed dataset."""
    model_version = "meter-ocr-baseline-v1"
    name = "OCR_BASELINE"

    def __init__(self) -> None:
        self.detector = MeterDetector()
        self.customer_ocr = CustomerOcr()
        self.meter_reader = MeterReader()

    def process(self, image_path: Path) -> dict:
        started = perf_counter()
        quality = assess_image_quality(image_path)
        source = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if source is None:
            raise ValueError("OpenCV could not decode the image.")
        prepared = prepare_for_detection(source)
        detection = self.detector.detect(prepared)

        lines = read_lines(prepared)
        customer_id, customer_confidence = self.customer_ocr.read(prepared, lines)
        meter_reading, meter_confidence = self.meter_reader.read(prepared, lines)
        validation = validate(customer_id, meter_reading)
        final_confidence = calculate(customer_confidence, meter_confidence, detection.confidence, quality["quality_score"], validation["valid"])
        return {"processor": self.name, "is_mock": False, "model_version": self.model_version, "customer_id_ai": customer_id, "meter_reading_ai": meter_reading, "customer_confidence": customer_confidence, "meter_confidence": meter_confidence, "detection_confidence": detection.confidence, "image_quality_score": quality["quality_score"], "final_confidence": final_confidence, "status": "REVIEW", "quality": quality, "validation": validation, "ocr_lines": len(lines), "regions": {"meter": detection.meter_region, "customer": detection.customer_region, "reading": detection.reading_region}, "processing_time_ms": round((perf_counter() - started) * 1000)}
