from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter

import cv2
from app.core.config import get_settings

from ai.pipeline.confidence import calculate
from ai.pipeline.customer_code_reader import CustomerCodeReader
from ai.pipeline.geometry import normalized_bbox_polygon, perspective_crop
from ai.pipeline.localization import MeterLocator, ReadingRegionLocator
from ai.pipeline.preprocessing import ImagePreprocessingModel
from ai.pipeline.quality import assess_image_quality
from ai.pipeline.scene_ocr import read_lines
from ai.pipeline.validator import validate
from ai.readers.consensus import ConsensusMeterReader
from ai.training.deep_locator import load_region_model


class MeterReadingPipeline:
    """Four-stage pipeline for locating and reading mechanical meters."""

    name = "OCR_BASELINE"

    def __init__(
        self,
        model_version: str | None = None,
        region_model_path: Path | None = None,
        meter_model_path: Path | None = None,
        parseq_model: dict | None = None,
    ) -> None:
        self.name = "FOUR_STAGE_METER_PIPELINE"
        self.model_version = model_version or "modern-sequence-consensus-v1"
        self.customer_code_reader = CustomerCodeReader()
        region_model = (
            load_region_model(region_model_path) if region_model_path else None
        )
        meter_model = load_region_model(meter_model_path) if meter_model_path else None
        self.has_region_model = region_model is not None
        self.has_meter_model = meter_model is not None
        self.image_preprocessor = ImagePreprocessingModel()
        self.meter_locator = MeterLocator(meter_model)
        self.reading_region_locator = ReadingRegionLocator(region_model)
        self.meter_reader = ConsensusMeterReader(parseq_model=parseq_model)
        self.has_fine_tuned_reader = parseq_model is not None

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
        preprocessed_at = perf_counter()
        # Quality is measured on the bounded image actually consumed downstream;
        # this avoids a full-resolution Laplacian pass on large phone photos.
        quality = assess_image_quality(prepared)
        quality_at = perf_counter()
        meter_location = self.meter_locator.locate(prepared)
        meter_at = perf_counter()
        reading_location = self.reading_region_locator.locate(prepared, meter_location)
        region_at = perf_counter()
        scene_ocr_skipped = reading_location.source.startswith("TRAINED_")
        lines = [] if scene_ocr_skipped else read_lines(prepared)
        scene_ocr_at = perf_counter()
        region_fallback_ms = 0.0
        if not scene_ocr_skipped:
            reading_location = self.reading_region_locator.locate(
                prepared, meter_location, lines, predict=False
            )
            region_fallback_ms = (perf_counter() - scene_ocr_at) * 1000
        localized_at = perf_counter()
        customer_stats = {}
        customer_x, customer_y, customer_width, customer_height = (
            meter_location.customer_region
        )
        customer_crop = prepared[
            customer_y : customer_y + customer_height,
            customer_x : customer_x + customer_width,
        ]
        reader_stats = {}
        if reading_location.reading_polygon is not None:
            reading_crop = perspective_crop(prepared, reading_location.reading_polygon)
        else:
            x, y, width, height = reading_location.reading_region
            reading_crop = prepared[y : y + height, x : x + width]
        cropped_at = perf_counter()

        def customer_ocr():
            customer_started = perf_counter()
            value = self.customer_code_reader.read(
                customer_crop,
                None if scene_ocr_skipped else lines,
                diagnostics=customer_stats,
            )
            return value, (perf_counter() - customer_started) * 1000

        # No database sessions cross threads; both tasks consume immutable image
        # views. Join before returning: an unverified code never becomes official.
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="customer-ocr"
        ) as executor:
            customer_future = executor.submit(customer_ocr)
            digits_started = perf_counter()
            meter_reading, meter_confidence = self.meter_reader.read(
                reading_crop,
                diagnostics=reader_stats,
                integer_digits=effective_integer_digits,
            )
            digits_at = perf_counter()
            (customer_id, customer_confidence), customer_ms = customer_future.result()
        read_at = perf_counter()
        reader_stats["digits_ready_ms"] = round((digits_at - started) * 1000, 2)
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
                    "fine_tuned_on_project": self.has_fine_tuned_reader,
                },
            },
            "quality": quality,
            "validation": validation,
            "ocr_lines": len(lines),
            "scene_ocr_skipped": scene_ocr_skipped,
            "regions": {
                "meter": meter_location.meter_region,
                "customer": meter_location.customer_region,
                "reading": reading_location.reading_region,
                "reading_polygon": reading_location.reading_polygon,
                "meter_polygon": meter_location.meter_polygon,
                "human_reading": None,
            },
            "reader_diagnostics": reader_stats,
            "customer_ocr_diagnostics": customer_stats,
            "timings_ms": {
                "decode": round((decoded_at - started) * 1000),
                "preprocess": round((preprocessed_at - decoded_at) * 1000, 2),
                "quality": round((quality_at - preprocessed_at) * 1000, 2),
                "meter_location": round((meter_at - quality_at) * 1000, 2),
                "reading_region": round(
                    (region_at - meter_at) * 1000 + region_fallback_ms, 2
                ),
                "scene_ocr": round((scene_ocr_at - region_at) * 1000, 2),
                "customer_ocr": round(customer_ms, 2),
                "customer_wait": round((read_at - digits_at) * 1000, 2),
                "crop": round((cropped_at - localized_at) * 1000, 2),
                "read_digits": round((digits_at - digits_started) * 1000, 2),
                "validation": round((perf_counter() - read_at) * 1000, 2),
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
