from pathlib import Path
from time import perf_counter

import cv2

from ai.pipeline.confidence import calculate
from ai.pipeline.customer_code_reader import CustomerCodeReader
from ai.pipeline.geometry import normalized_bbox_polygon, perspective_crop
from ai.pipeline.localization import MeterLocator, ReadingRegionLocator
from ai.readers.consensus import ConsensusMeterReader
from ai.pipeline.preprocessing import ImagePreprocessingModel
from ai.pipeline.quality import assess_image_quality
from ai.pipeline.scene_ocr import read_lines
from ai.pipeline.validator import validate
from ai.training.keypoint_regressor import KeypointRegionRegressor
from app.core.config import get_settings


class MeterReadingPipeline:
    """Four-stage pipeline for locating and reading mechanical meters."""

    name = "OCR_BASELINE"

    def __init__(
        self,
        model_version: str | None = None,
        region_model_path: Path | None = None,
        meter_model_path: Path | None = None,
    ) -> None:
        self.name = "FOUR_STAGE_METER_PIPELINE"
        self.model_version = model_version or "modern-sequence-consensus-v1"
        self.customer_code_reader = CustomerCodeReader()
        region_model = (
            KeypointRegionRegressor.load(region_model_path)
            if region_model_path
            else None
        )
        meter_model = (
            KeypointRegionRegressor.load(meter_model_path) if meter_model_path else None
        )
        self.has_region_model = region_model is not None
        self.has_meter_model = meter_model is not None
        self.image_preprocessor = ImagePreprocessingModel()
        self.meter_locator = MeterLocator(meter_model)
        self.reading_region_locator = ReadingRegionLocator(region_model)
        self.meter_reader = ConsensusMeterReader()

    def process(
        self,
        image_path: Path,
        reading_bbox: tuple[float, float, float, float] | None = None,
        reading_polygon: tuple[tuple[float, float], ...] | None = None,
        integer_digits: int | None = None,
    ) -> dict:
        started = perf_counter()
        effective_integer_digits = (
            integer_digits or get_settings().meter_integer_digits_default
        )
        source = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if source is None:
            raise ValueError("OpenCV không thể giải mã hình ảnh.")
        decoded_at = perf_counter()
        selected_polygon = reading_polygon or (
            normalized_bbox_polygon(reading_bbox) if reading_bbox is not None else None
        )
        if selected_polygon is not None:
            return self._process_selected_region(
                source, selected_polygon, started, decoded_at, integer_digits
            )
        prepared, preprocessing_confidence, preprocessing_operations = (
            self.image_preprocessor.process(source)
        )
        # Quality is measured on the bounded image actually consumed downstream;
        # this avoids a full-resolution Laplacian pass on large phone photos.
        quality = assess_image_quality(prepared)
        lines = read_lines(prepared)
        scene_ocr_at = perf_counter()
        meter_location = self.meter_locator.locate(prepared)
        reading_location = self.reading_region_locator.locate(
            prepared, meter_location, lines
        )
        customer_stats = {}
        customer_x, customer_y, customer_width, customer_height = (
            meter_location.customer_region
        )
        customer_crop = prepared[
            customer_y : customer_y + customer_height,
            customer_x : customer_x + customer_width,
        ]
        customer_id, customer_confidence = self.customer_code_reader.read(
            customer_crop, lines, diagnostics=customer_stats
        )
        located_at = perf_counter()
        reader_stats = {}
        if reading_location.reading_polygon is not None:
            reading_crop = perspective_crop(prepared, reading_location.reading_polygon)
            meter_reading, meter_confidence = self.meter_reader.read(
                reading_crop,
                diagnostics=reader_stats,
                integer_digits=effective_integer_digits,
            )
        else:
            x, y, width, height = reading_location.reading_region
            reading_crop = prepared[y : y + height, x : x + width]
            meter_reading, meter_confidence = self.meter_reader.read(
                reading_crop,
                diagnostics=reader_stats,
                integer_digits=effective_integer_digits,
            )
        read_at = perf_counter()
        validation = validate(customer_id, meter_reading)
        final_confidence = calculate(
            customer_confidence,
            meter_confidence,
            reading_location.confidence,
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
            "detection_confidence": reading_location.confidence,
            "image_quality_score": quality["quality_score"],
            "final_confidence": final_confidence,
            "status": "REVIEW",
            "human_region_requested": False,
            "detection_source": reading_location.source,
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
                    "trained": self.has_meter_model,
                },
                "reading_region": {
                    "name": self.reading_region_locator.name,
                    "version": self.reading_region_locator.version,
                    "confidence": reading_location.confidence,
                    "source": reading_location.source,
                    "trained": self.has_region_model,
                },
                "meter_reader": {
                    "name": self.meter_reader.name,
                    "version": self.model_version,
                    "confidence": meter_confidence,
                    "trained": True,
                },
            },
            "quality": quality,
            "validation": validation,
            "ocr_lines": len(lines),
            "regions": {
                "meter": meter_location.meter_region,
                "customer": meter_location.customer_region,
                "reading": reading_location.reading_region,
                "reading_polygon": reading_location.reading_polygon,
                "human_reading": None,
            },
            "reader_diagnostics": reader_stats,
            "customer_ocr_diagnostics": customer_stats,
            "timings_ms": {
                "decode": round((decoded_at - started) * 1000),
                "preprocess_quality_scene_ocr": round(
                    (scene_ocr_at - decoded_at) * 1000
                ),
                "localization_customer_ocr": round((located_at - scene_ocr_at) * 1000),
                "crop_and_read_digits": round((read_at - located_at) * 1000),
            },
            "processing_time_ms": round((perf_counter() - started) * 1000),
        }

    def _process_selected_region(
        self, source, polygon, started, decoded_at, integer_digits=None
    ) -> dict:
        # Match training preprocessing without scene OCR or automatic detection.
        prepared, _, operations = self.image_preprocessor.process(source)
        prepared_at = perf_counter()
        crop = perspective_crop(prepared, polygon)
        quality = assess_image_quality(crop)
        cropped_at = perf_counter()
        reader_stats = {}
        value, confidence = self.meter_reader.read(
            crop,
            diagnostics=reader_stats,
            integer_digits=integer_digits
            or get_settings().meter_integer_digits_default,
        )
        finished = perf_counter()
        height, width = prepared.shape[:2]
        return {
            "processor": self.name,
            "model_version": self.model_version,
            "is_mock": False,
            "reading_only": True,
            "integer_digits": integer_digits,
            "human_region_requested": True,
            "customer_id_ai": None,
            "customer_confidence": 0.0,
            "meter_reading_ai": value,
            "meter_confidence": confidence,
            "detection_confidence": 1.0,
            "image_quality_score": quality["quality_score"],
            "final_confidence": confidence,
            "status": "REVIEW",
            "detection_source": "HUMAN_REVIEW",
            "quality": quality,
            "preprocessing_operations": list(operations),
            "skipped_stages": [
                "scene_ocr",
                "meter_location",
                "reading_region",
                "customer_ocr",
            ],
            "regions": {
                "human_reading": [
                    [round(x * width), round(y * height)] for x, y in polygon
                ]
            },
            "reader_diagnostics": reader_stats,
            "timings_ms": {
                "decode": round((decoded_at - started) * 1000),
                "preprocess": round((prepared_at - decoded_at) * 1000),
                "crop_and_quality": round((cropped_at - prepared_at) * 1000),
                "read_digits": round((finished - cropped_at) * 1000),
            },
            "processing_time_ms": round((finished - started) * 1000),
        }
