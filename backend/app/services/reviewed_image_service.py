import os
import re
import shutil
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.models.image import ImageRecord
from app.services.storage_service import resolve_storage_path

_INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_SUPPORTED_EXTENSIONS = {".jpg", ".png", ".webp"}
_REVIEW_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def _safe_customer_filename(customer_code: str) -> str:
    normalized = unicodedata.normalize("NFKC", customer_code).strip()
    safe = _INVALID_FILENAME_CHARACTERS.sub("_", normalized).rstrip(". ")
    safe = re.sub(r"\s+", "_", safe)[:128]
    if not safe or safe.upper() in _WINDOWS_RESERVED_NAMES:
        raise ValueError("Mã khách hàng không thể dùng làm tên tệp an toàn.")
    return safe


def _archive_directory(storage_root: Path, reviewed_at: datetime) -> Path:
    local_date = reviewed_at.astimezone(_REVIEW_TIMEZONE)
    directory = (storage_root / "reviewed" / local_date.strftime("%d-%m-%Y")).resolve()
    reviewed_root = (storage_root / "reviewed").resolve()
    if not directory.is_relative_to(reviewed_root):
        raise RuntimeError("Unsafe reviewed image destination.")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _write_exclusive_copy(source: Path, destination: Path) -> bool:
    try:
        with destination.open("xb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output, length=1024 * 1024)
        shutil.copystat(source, destination)
        return True
    except FileExistsError:
        return False
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def _replace_copy(source: Path, destination: Path) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=".reviewed-",
            suffix=destination.suffix,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, temporary, length=1024 * 1024)
        shutil.copystat(source, temporary_path)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def archive_reviewed_image(image: ImageRecord, customer_code: str, reviewed_at: datetime) -> str:
    """Copy a confirmed image into a date folder and retain the original upload."""
    settings = get_settings()
    storage_root = settings.storage_root.resolve()
    source = resolve_storage_path(image.relative_path)
    extension = source.suffix.lower()
    if extension not in _SUPPORTED_EXTENSIONS:
        raise ValueError("Định dạng ảnh lưu trữ không được hỗ trợ.")

    directory = _archive_directory(storage_root, reviewed_at)
    filename_base = _safe_customer_filename(customer_code)
    current_path = (storage_root / image.reviewed_path).resolve() if image.reviewed_path else None
    if current_path is not None and not current_path.is_relative_to(storage_root / "reviewed"):
        raise RuntimeError("Unsafe existing reviewed image path.")

    destination: Path | None = None
    for number in range(1, 10_001):
        suffix = "" if number == 1 else f"_{number}"
        candidate = directory / f"{filename_base}{suffix}{extension}"
        if current_path == candidate:
            _replace_copy(source, candidate)
            destination = candidate
            break
        if _write_exclusive_copy(source, candidate):
            destination = candidate
            break
    if destination is None:
        raise RuntimeError("Không thể cấp tên tệp cho ảnh đã kiểm tra.")

    if current_path is not None and current_path != destination:
        current_path.unlink(missing_ok=True)
    relative_path = destination.relative_to(storage_root).as_posix()
    image.reviewed_path = relative_path
    return relative_path


def remove_reviewed_image(image: ImageRecord) -> str | None:
    """Remove a former confirmed copy when a result is explicitly rejected."""
    if not image.reviewed_path:
        return None
    storage_root = get_settings().storage_root.resolve()
    reviewed_root = (storage_root / "reviewed").resolve()
    archived_path = (storage_root / image.reviewed_path).resolve()
    if not archived_path.is_relative_to(reviewed_root):
        raise RuntimeError("Unsafe reviewed image path.")
    previous_path = image.reviewed_path
    archived_path.unlink(missing_ok=True)
    image.reviewed_path = None
    return previous_path
