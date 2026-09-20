import unittest

from ai.pipeline.customer_ocr import CustomerOcr
from ai.pipeline.meter_reader import MeterReader
from ai.pipeline.validator import validate


class CustomerOcrTests(unittest.TestCase):
    def test_normalizes_common_ocr_confusions_in_numeric_suffix(self) -> None:
        self.assertEqual(CustomerOcr._normalize("KHOO4"), "KH004")

    def test_rejects_identifier_without_suffix(self) -> None:
        self.assertIsNone(CustomerOcr._normalize("KH"))


class ValidatorTests(unittest.TestCase):
    def test_accepts_integer_mechanical_meter_reading(self) -> None:
        self.assertEqual(validate("KH004", "63751"), {"valid": True, "errors": []})

    def test_rejects_decimal_meter_reading(self) -> None:
        self.assertIn("invalid_meter_reading", validate("KH004", "63751.3")["errors"])

    def test_rejects_short_or_non_numeric_reading(self) -> None:
        result = validate("KH004", "22OV")
        self.assertFalse(result["valid"])
        self.assertIn("invalid_meter_reading", result["errors"])


class MeterReaderTests(unittest.TestCase):
    def test_ignores_digits_after_decimal_separator(self) -> None:
        self.assertEqual(MeterReader._integer_groups("63751.3 kWh"), ["63751"])
        self.assertEqual(MeterReader._integer_groups("05068,4 kWh"), ["05068"])


if __name__ == "__main__":
    unittest.main()
