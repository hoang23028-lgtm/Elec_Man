from hashlib import sha256
from pathlib import Path
from time import perf_counter

import cv2

from ai.pipeline.confidence import calculate
from ai.pipeline.customer_ocr import MockCustomerOcr
from ai.pipeline.detector import MockDetector
from ai.pipeline.meter_reader import MockMeterReader
from ai.pipeline.preprocessing import prepare_for_detection
from ai.pipeline.quality import assess_image_quality
from ai.pipeline.validator import validate


class DevelopmentPipeline:
    """Pipeline contract used until approved trained models are supplied."""
    model_version = "mock-pipeline-v1"
    name = "MOCK"

    def __init__(self) -> None:
        self.detector = MockDetector()
        self.customer_ocr = MockCustomerOcr()
        self.meter_reader = MockMeterReader()

    def process(self, image_path: Path) -> dict:
        started = perf_counter()
        quality = assess_image_quality(image_path)
        source = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if source is None:
            raise ValueError("OpenCV could not decode the image.")
        detection = self.detector.detect(prepare_for_detection(source))
        # The development processor must never claim to read a real meter.
        # Stable, clearly synthetic values let users exercise the review and
        # export workflow before approved models are connected.
        digest = sha256(image_path.read_bytes()).hexdigest()
        customer_id = f"MOCK-{digest[:8].upper()}"
        meter_reading = str(10_000 + int(digest[8:14], 16) % 90_000)
        customer_confidence = 0.72
        meter_confidence = 0.68
        validation = validate(customer_id, meter_reading)
        final_confidence = calculate(customer_confidence, meter_confidence, detection.confidence, quality["quality_score"], validation["valid"])
        return {"processor": "MOCK", "is_mock": True, "model_version": self.model_version, "customer_id_ai": customer_id, "meter_reading_ai": meter_reading, "customer_confidence": customer_confidence, "meter_confidence": meter_confidence, "detection_confidence": detection.confidence, "image_quality_score": quality["quality_score"], "final_confidence": final_confidence, "status": "REVIEW", "quality": quality, "validation": validation, "processing_time_ms": round((perf_counter() - started) * 1000)}
