"""Explicit development-only processor used to validate asynchronous job flow."""
from pathlib import Path
from time import perf_counter


class MockProcessor:
    name = "MOCK"

    def process(self, image_path: Path) -> dict:
        started = perf_counter()
        if not image_path.is_file():
            raise FileNotFoundError("Image file is unavailable.")
        return {"processor": self.name, "is_mock": True, "message": "No customer ID or meter reading was inferred.", "processing_time_ms": round((perf_counter() - started) * 1000, 2)}
