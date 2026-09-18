import unittest

from ai.pipeline.customer_ocr import CustomerOcr
from ai.pipeline.validator import validate


class CustomerOcrTests(unittest.TestCase):
    def test_normalizes_common_ocr_confusions_in_numeric_suffix(self) -> None:
        self.assertEqual(CustomerOcr._normalize("KHOO4"), "KH004")

    def test_rejects_identifier_without_suffix(self) -> None:
        self.assertIsNone(CustomerOcr._normalize("KH"))


class ValidatorTests(unittest.TestCase):
    def test_accepts_mechanical_meter_reading_with_tenths(self) -> None:
        self.assertEqual(validate("KH004", "63751.3"), {"valid": True, "errors": []})

    def test_rejects_short_or_non_numeric_reading(self) -> None:
        result = validate("KH004", "22OV")
        self.assertFalse(result["valid"])
        self.assertIn("invalid_meter_reading", result["errors"])


if __name__ == "__main__":
    unittest.main()
