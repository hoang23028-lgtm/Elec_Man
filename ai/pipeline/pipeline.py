from pathlib import Path
from time import perf_counter

import cv2

from ai.pipeline.confidence import calculate
from ai.pipeline.customer_ocr import CustomerOcr
from ai.pipeline.detector import Detection, MeterLocatorModel, ReadingRegionModel
from ai.pipeline.geometry import normalized_bbox_polygon, perspective_crop
from ai.pipeline.meter_reader import MeterReader
from ai.pipeline.preprocessing import ImagePreprocessingModel
from ai.pipeline.quality import assess_image_quality
from ai.pipeline.rapid import read_lines
from ai.pipeline.validator import validate
from ai.training.digit_model import load_digit_model
from ai.training.region_model import ReadingRegionRegressor


class DevelopmentPipeline:
    """Pretrained OCR baseline for bootstrapping a human-reviewed dataset."""

    name = "OCR_BASELINE"

    def __init__(
        self,
        digit_model_path: Path | None = None,
        model_version: str | None = None,
        region_model_path: Path | None = None,
    ) -> None:
        self.name = "FOUR_STAGE_METER_PIPELINE"
        self.model_version = model_version or "meter-ocr-baseline-v2-integer"
        self.customer_ocr = CustomerOcr()
        trained_model = load_digit_model(digit_model_path) if digit_model_path else None
        region_model = (
            ReadingRegionRegressor.load(region_model_path)
            if region_model_path
            else trained_model
        )
        self.has_trained_models = trained_model is not None
        self.has_region_model = region_model is not None
        self.image_preprocessor = ImagePreprocessingModel()
        self.meter_locator = MeterLocatorModel()
        self.reading_region_model = ReadingRegionModel(region_model)
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
        prepared, preprocessing_confidence, preprocessing_operations = (
            self.image_preprocessor.process(source)
        )
        lines = read_lines(prepared)
        meter_location = self.meter_locator.locate(prepared)
        reading_location = self.reading_region_model.locate(
            prepared, meter_location, lines
        )
        detection = Detection(
            reading_location.confidence,
            meter_location.meter_region,
            meter_location.customer_region,
            reading_location.reading_region,
            reading_location.reading_polygon,
            reading_location.source,
        )
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
            "stage_models": {
                "image_preprocessing": {
                    "name": self.image_preprocessor.name,
                    "version": self.image_preprocessor.version,
                    "confidence": preprocessing_confidence,
                    "operations": list(preprocessing_operations),
                    "trained": False,
                },
                "meter_location": {
                    "name": self.meter_locator.name,
                    "version": self.meter_locator.version,
                    "confidence": meter_location.confidence,
                    "source": meter_location.source,
                    "trained": False,
                },
                "reading_region": {
                    "name": self.reading_region_model.name,
                    "version": self.reading_region_model.version,
                    "confidence": 1.0
                    if selected_polygon is not None
                    else reading_location.confidence,
                    "source": "HUMAN_REVIEW"
                    if selected_polygon is not None
                    else reading_location.source,
                    "trained": self.has_region_model,
                },
                "meter_reader": {
                    "name": "specialized-digit-reader"
                    if self.has_trained_models
                    else "ocr-reader-baseline",
                    "version": self.model_version,
                    "confidence": meter_confidence,
                    "trained": self.has_trained_models,
                },
            },
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
