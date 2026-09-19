from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading


def _excel_text(value: str | None) -> str:
    text = value or ""
    return f"'{text}" if text[:1] in {"=", "+", "-", "@"} else text


def _excel_datetime(value: datetime | None) -> datetime | None:
    """Excel stores naive datetimes; normalize reviewed timestamps to UTC."""
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


def create_final_export(db: Session) -> tuple[str, Path]:
    statement = (
        select(ImageRecord, MeterReading)
        .join(MeterReading, MeterReading.image_id == ImageRecord.id)
        .where(MeterReading.review_status == "CONFIRMED")
        .order_by(ImageRecord.created_at)
        .execution_options(yield_per=1000)
    )
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Chỉ số đã xác nhận")
    sheet.freeze_panes = "A2"
    for column, width in {"A": 38, "B": 32, "C": 22, "D": 18, "E": 18, "F": 24}.items():
        sheet.column_dimensions[column].width = width
    headers = [
        "Mã hình ảnh",
        "Tên tệp gốc",
        "Mã khách hàng",
        "Chỉ số điện",
        "Trạng thái kiểm duyệt",
        "Thời gian kiểm duyệt",
    ]
    header_cells = [WriteOnlyCell(sheet, value=value) for value in headers]
    for cell in header_cells:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0B7285")
    sheet.append(header_cells)
    row_count = 1
    for image, reading in db.execute(statement):
        sheet.append(
            [
                str(image.id),
                _excel_text(image.original_filename),
                _excel_text(reading.final_customer_id),
                _excel_text(reading.final_meter_reading),
                "Đã xác nhận",
                _excel_datetime(reading.reviewed_at),
            ]
        )
        row_count += 1
    sheet.auto_filter.ref = f"A1:F{row_count}"
    root = get_settings().storage_root
    directory = root / "exports" / f"{datetime.now(UTC):%Y}" / f"{datetime.now(UTC):%m}"
    directory.mkdir(parents=True, exist_ok=True)
    name = f"chi-so-da-xac-nhan-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}.xlsx"
    path = directory / name
    workbook.save(path)
    return name, path
