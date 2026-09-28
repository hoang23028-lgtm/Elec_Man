import unittest

import numpy as np

from ai.pipeline.customer_ocr import CustomerOcr
from ai.pipeline.detector import MeterDetector, MeterLocatorModel, ReadingRegionModel
from ai.pipeline.meter_reader import MeterReader
from ai.pipeline.preprocessing import ImagePreprocessingModel
from ai.pipeline.rapid import TextLine
from ai.pipeline.validator import validate


class CustomerOcrTests(unittest.TestCase):
    def test_normalizes_common_ocr_confusions_in_numeric_suffix(self) -> None:
        self.assertEqual(CustomerOcr._normalize("KHOO4"), "KH004")

    def test_rejects_identifier_without_suffix(self) -> None:
        self.assertIsNone(CustomerOcr._normalize("KH"))

    def test_preserves_customer_code_punctuation(self) -> None:
        self.assertEqual(CustomerOcr._normalize("PN2.001"), "PN2.001")


class ValidatorTests(unittest.TestCase):
    def test_accepts_integer_mechanical_meter_reading(self) -> None:
        self.assertEqual(validate("KH004", "63751"), {"valid": True, "errors": []})

    def test_rejects_decimal_meter_reading(self) -> None:
        self.assertIn("invalid_meter_reading", validate("KH004", "63751.3")["errors"])

    def test_accepts_customer_code_with_dot(self) -> None:
        self.assertTrue(validate("PN2.001", "63751")["valid"])

    def test_rejects_short_or_non_numeric_reading(self) -> None:
        result = validate("KH004", "22OV")
        self.assertFalse(result["valid"])
        self.assertIn("invalid_meter_reading", result["errors"])


class MeterReaderTests(unittest.TestCase):
    def test_ignores_digits_after_decimal_separator(self) -> None:
        self.assertEqual(MeterReader._integer_groups("63751.3 kWh"), ["63751"])
        self.assertEqual(MeterReader._integer_groups("05068,4 kWh"), ["05068"])

    def test_specialized_model_can_read_without_generic_ocr_result(self) -> None:
        class SpecializedModel:
            feature_mode = "raw"

            @staticmethod
            def candidate_lengths() -> tuple[int, ...]:
                return (5,)

            @staticmethod
            def predict_features(features):
                return ("12345", 0.96) if len(features) == 5 else ("", 0.0)

        image = np.full((40, 200, 3), 128, dtype=np.uint8)
        value, confidence = MeterReader(SpecializedModel()).read(
            image, [], (0.0, 0.0, 1.0, 1.0)
        )

        self.assertEqual(value, "12345")
        self.assertGreater(confidence, 0.9)


class MeterDetectorTests(unittest.TestCase):
    def test_four_stage_vision_models_run_independently(self) -> None:
        image = np.full((300, 500, 3), 110, dtype=np.uint8)
        prepared, confidence, operations = ImagePreprocessingModel().process(image)
        meter = MeterLocatorModel().locate(prepared)
        reading = ReadingRegionModel().locate(prepared, meter, [])

        self.assertEqual(prepared.shape, image.shape)
        self.assertGreater(confidence, 0)
        self.assertTrue(operations)
        self.assertEqual(len(meter.meter_region), 4)
        self.assertEqual(len(reading.reading_region), 4)

    def test_prefers_numeric_ocr_line_over_fixed_ratio(self) -> None:
        image = np.zeros((300, 500, 3), dtype=np.uint8)
        line = TextLine(
            ((120.0, 130.0), (350.0, 130.0), (350.0, 170.0), (120.0, 170.0)),
            "063751",
            0.91,
        )

        detection = MeterDetector().detect(image, [line])

        self.assertEqual(detection.source, "SCENE_OCR")
        self.assertLess(detection.reading_region[0], 120)
        self.assertGreater(detection.reading_region[2], 230)


if __name__ == "__main__":
    unittest.main()
