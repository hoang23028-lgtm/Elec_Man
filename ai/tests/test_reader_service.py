import base64

import cv2
import numpy as np
import pytest
from fastapi import HTTPException

from ai.services import sequence_reader as reader_service


class FakeReader:
    name = "fake"

    @staticmethod
    def predict(_image, integer_digits):
        assert integer_digits == 5
        return "12345", 0.89


def test_reader_service_decodes_and_returns_consensus(monkeypatch):
    image = np.full((30, 160, 3), 120, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    monkeypatch.setattr(reader_service, "reader", FakeReader())

    result = reader_service.read_register(
        reader_service.ReadRequest(
            image_base64=base64.b64encode(encoded).decode(),
            integer_digits=5,
        )
    )

    assert result.value == "12345"
    assert result.confidence == 0.89
    assert result.diagnostics["reader"] == FakeReader.name


def test_reader_service_rejects_invalid_image(monkeypatch):
    monkeypatch.setattr(reader_service, "reader", FakeReader())
    with pytest.raises(HTTPException) as error:
        reader_service.read_register(
            reader_service.ReadRequest(
                image_base64=base64.b64encode(b"not-an-image").decode(),
                integer_digits=5,
            )
        )
    assert error.value.status_code == 422
