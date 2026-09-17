from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading

def _excel_text(value: str | None) -> str:
    text = value or ""
    return f"'{text}" if text[:1] in {"=", "+", "-", "@"} else text

def create_final_export(db: Session) -> tuple[str, Path]:
    rows = db.execute(select(ImageRecord, MeterReading).join(MeterReading, MeterReading.image_id == ImageRecord.id).where(MeterReading.review_status == "CONFIRMED").order_by(ImageRecord.created_at)).all()
    workbook = Workbook(); sheet = workbook.active; sheet.title = "Final readings"
    headers = ["Image ID", "Original filename", "Customer ID", "Meter reading", "Review status", "Reviewed at"]
    sheet.append(headers)
    for cell in sheet[1]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="0B7285")
    for image, reading in rows:
        sheet.append([str(image.id), _excel_text(image.original_filename), _excel_text(reading.final_customer_id), _excel_text(reading.final_meter_reading), reading.review_status, reading.reviewed_at])
    sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions
    for column, width in {"A": 38, "B": 32, "C": 22, "D": 18, "E": 18, "F": 24}.items(): sheet.column_dimensions[column].width = width
    root = get_settings().storage_root; directory = root / "exports" / f"{datetime.now(UTC):%Y}" / f"{datetime.now(UTC):%m}"; directory.mkdir(parents=True, exist_ok=True)
    name = f"final-readings-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}.xlsx"; path = directory / name; workbook.save(path)
    return name, path
