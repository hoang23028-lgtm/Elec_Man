from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Detection:
    confidence: float
    meter_region: tuple[int, int, int, int] | None
    customer_region: tuple[int, int, int, int] | None
    reading_region: tuple[int, int, int, int] | None


class MockDetector:
    """Development-only interface implementation; it does not detect objects."""
    model_version = "mock-pipeline-v0"

    def detect(self, _: np.ndarray) -> Detection:
        return Detection(confidence=0.65, meter_region=None, customer_region=None, reading_region=None)
