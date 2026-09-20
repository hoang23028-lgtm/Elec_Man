import hashlib
import os
import tempfile
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

_FORMATS = {
    "JPEG": ("jpg", "image/jpeg", b"\xff\xd8\xff"),
    "PNG": ("png", "image/png", b"\x89PNG\r\n\x1a\n"),
    "WEBP": ("webp", "image/webp", b"RIFF"),
}


@dataclass(frozen=True)
class StoredUpload:
    original_filename: str
    stored_filename: str
    relative_path: str
    thumbnail_path: str
    file_size: int
    mime_type: str
    sha256: str
    width: int
    height: int
    absolute_path: Path
    thumbnail_absolute_path: Path


def _bad_upload(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


def _safe_original_name(filename: str | None) -> str:
    name = Path(filename or "upload").name.strip()
    if not name or name in {".", ".."} or any(ord(char) < 32 for char in name):
        raise _bad_upload("Tên tệp không hợp lệ.")
    return name[:255]


def _validate_signature(sample: bytes, extension: str) -> None:
    if extension == "webp":
        valid = sample.startswith(b"RIFF") and sample[8:12] == b"WEBP"
    else:
        expected = (
            _FORMATS[{"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG"}.get(extension, "")][2]
            if extension in {"jpg", "jpeg", "png"}
            else b""
        )
        valid = bool(expected) and sample.startswith(expected)
    if not valid:
        raise _bad_upload("Dấu hiệu tệp không khớp với định dạng ảnh được hỗ trợ.")


async def store_upload(file: UploadFile, batch_id: UUID) -> StoredUpload:
    settings = get_settings()
    original_filename = _safe_original_name(file.filename)
    extension = Path(original_filename).suffix.lower().lstrip(".")
    if extension == "jpeg":
        extension = "jpg"
    if extension not in {"jpg", "png", "webp"}:
        raise _bad_upload("Chỉ chấp nhận ảnh JPEG, PNG và WEBP.")
    claimed_mime = (file.content_type or "").lower()
    if claimed_mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise _bad_upload("Kiểu nội dung khai báo không được hỗ trợ.")

    now = datetime.now(UTC)
    relative_dir = Path("original") / f"{now:%Y}" / f"{now:%m}" / str(batch_id)
    storage_root = settings.storage_root.resolve()
    destination_dir = (storage_root / relative_dir).resolve()
    if not destination_dir.is_relative_to(storage_root):
        raise RuntimeError("Unsafe storage destination.")
    destination_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = settings.max_image_size_mb * 1024 * 1024
    digest = hashlib.sha256()
    total_size = 0
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination_dir, prefix=".upload-", delete=False
        ) as temp:
            temp_path = Path(temp.name)
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > max_bytes:
                    raise _bad_upload(f"Ảnh vượt quá giới hạn {settings.max_image_size_mb} MB.")
                digest.update(chunk)
                temp.write(chunk)
        # Reading only the signature avoids loading a potentially 100 MB upload
        # into memory before Pillow performs its bounded decode checks.
        with temp_path.open("rb") as stored_file:
            sample = stored_file.read(16)
        _validate_signature(sample, extension)
        try:
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(temp_path, formats=("JPEG", "PNG", "WEBP")) as image:
                actual_format = image.format
                image.verify()
            with Image.open(temp_path, formats=("JPEG", "PNG", "WEBP")) as image:
                width, height = image.size
                if width * height > settings.max_image_pixels:
                    raise _bad_upload("Kích thước ảnh vượt quá giới hạn điểm ảnh đã cấu hình.")
                if actual_format not in _FORMATS:
                    raise _bad_upload("Định dạng ảnh sau khi giải mã không được hỗ trợ.")
                expected_extension, actual_mime, _ = _FORMATS[actual_format]
                if expected_extension != extension or actual_mime != claimed_mime:
                    raise _bad_upload(
                        "Phần mở rộng hoặc kiểu tệp khai báo không khớp với định dạng ảnh thực tế."
                    )
                thumbnail_relative = (
                    Path("thumbnails")
                    / f"{now:%Y}"
                    / f"{now:%m}"
                    / str(batch_id)
                    / f"{uuid4()}.jpg"
                )
                thumbnail_absolute = storage_root / thumbnail_relative
                thumbnail_absolute.parent.mkdir(parents=True, exist_ok=True)
                thumbnail = image.convert("RGB")
                thumbnail.thumbnail((400, 400))
                thumbnail.save(thumbnail_absolute, "JPEG", quality=82, optimize=True)
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise _bad_upload("Không thể giải mã tệp thành ảnh một cách an toàn.") from exc
        stored_filename = f"{uuid4()}.{extension}"
        relative_path = relative_dir / stored_filename
        absolute_path = storage_root / relative_path
        os.replace(temp_path, absolute_path)
        temp_path = None
        return StoredUpload(
            original_filename=original_filename,
            stored_filename=stored_filename,
            relative_path=relative_path.as_posix(),
            thumbnail_path=thumbnail_relative.as_posix(),
            file_size=total_size,
            mime_type=actual_mime,
            sha256=digest.hexdigest(),
            width=width,
            height=height,
            absolute_path=absolute_path,
            thumbnail_absolute_path=thumbnail_absolute,
        )
    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


def delete_stored_upload(upload: StoredUpload) -> None:
    upload.absolute_path.unlink(missing_ok=True)
    upload.thumbnail_absolute_path.unlink(missing_ok=True)


def resolve_storage_path(relative_path: str) -> Path:
    root = get_settings().storage_root.resolve()
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ảnh.")
    return target
