"""Internal inference service for modern whole-register readers."""

import base64
import binascii
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai.readers.sequence import PaddleV6SmallReader, ParseqTinyReader
from ai.pipeline.register import integer_register_strip

MAX_ENCODED_BYTES = 8 * 1024 * 1024
reader: PaddleV6SmallReader | ParseqTinyReader | None = None
reader_backend = os.environ.get("READER_BACKEND", "")
reader_lock = Lock()


class ReadRequest(BaseModel):
    image_base64: str = Field(min_length=8, max_length=MAX_ENCODED_BYTES)
    integer_digits: int = Field(ge=4, le=8)


class ReadResponse(BaseModel):
    value: str | None
    confidence: float
    diagnostics: dict


@asynccontextmanager
async def lifespan(_: FastAPI):
    global reader
    if reader_backend == "ppocr":
        reader = PaddleV6SmallReader()
    elif reader_backend == "parseq":
        reader = ParseqTinyReader(Path("/opt/parseq"))
    else:
        raise RuntimeError("READER_BACKEND phải là ppocr hoặc parseq.")
    yield
    reader = None


app = FastAPI(
    title="Dịch vụ đọc chỉ số công tơ",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    if reader is None:
        raise HTTPException(status_code=503, detail="Model chưa sẵn sàng.")
    return {"status": "ready"}


@app.post("/v1/read", response_model=ReadResponse)
def read_register(payload: ReadRequest) -> ReadResponse:
    if reader is None:
        raise HTTPException(status_code=503, detail="Model chưa sẵn sàng.")
    try:
        raw = base64.b64decode(payload.image_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(
            status_code=422, detail="Dữ liệu ảnh không hợp lệ."
        ) from exc
    if not raw or len(raw) > MAX_ENCODED_BYTES:
        raise HTTPException(status_code=413, detail="Ảnh vượt quá giới hạn.")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise HTTPException(status_code=422, detail="Không thể giải mã ảnh.")
    strip = integer_register_strip(image)
    with reader_lock:
        value, confidence = reader.predict(strip, payload.integer_digits)
    return ReadResponse(
        value=value,
        confidence=confidence,
        diagnostics={"reader": reader.name, "backend": reader_backend},
    )
