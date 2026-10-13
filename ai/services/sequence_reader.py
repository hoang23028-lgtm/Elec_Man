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
from pydantic import BaseModel, Field, model_validator

from ai.pipeline.register import integer_register_strip
from ai.readers.sequence import PaddleV6SmallReader, ParseqTinyReader

MAX_ENCODED_BYTES = 8 * 1024 * 1024
reader: PaddleV6SmallReader | ParseqTinyReader | None = None
reader_backend = os.environ.get("READER_BACKEND", "")
reader_lock = Lock()


class ReadRequest(BaseModel):
    image_base64: str = Field(min_length=8, max_length=MAX_ENCODED_BYTES)
    integer_digits: int = Field(ge=4, le=8)
    model_file: str | None = Field(default=None, max_length=500)
    model_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def paired_model(self):
        if bool(self.model_file) != bool(self.model_sha256):
            raise ValueError("Cần cả đường dẫn và checksum artifact.")
        return self


class ReadResponse(BaseModel):
    value: str | None
    confidence: float = Field(ge=0, le=1)
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
        if payload.model_file:
            root = Path("/models").resolve()
            path = (root / payload.model_file).resolve()
            if (
                reader_backend != "parseq"
                or not path.is_relative_to(root)
                or not path.is_file()
            ):
                raise HTTPException(422, "Artifact bộ đọc không khả dụng.")
            try:
                reader.load_checkpoint(path, payload.model_sha256)
            except (ValueError, OSError, RuntimeError) as error:
                raise HTTPException(
                    422, "Không thể xác minh artifact bộ đọc."
                ) from error
        elif isinstance(reader, ParseqTinyReader):
            reader.reset_checkpoint()
        value, confidence = reader.predict(strip, payload.integer_digits)
    return ReadResponse(
        value=value,
        confidence=confidence,
        diagnostics={"reader": reader.name, "backend": reader_backend},
    )
