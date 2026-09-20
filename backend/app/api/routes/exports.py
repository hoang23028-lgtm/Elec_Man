from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.meter_reading import MeterReading
from app.models.user import User
from app.security.dependencies import get_current_user, require_csrf
from app.services.export_service import create_final_export, resolve_export_path

router = APIRouter()


@router.post("/final", dependencies=[Depends(require_csrf)])
def export_final(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    name, _ = create_final_export(db)
    exported_rows = int(
        db.scalar(
            select(func.count(MeterReading.id)).where(
                MeterReading.review_status == "CONFIRMED"
            )
        )
        or 0
    )
    db.add(
        AuditLog(
            user_id=user.id,
            action="EXPORT_EXCEL",
            target_type="export",
            target_id=name,
            details_json={"filename": name, "exported_rows": exported_rows},
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    return {"filename": name, "download_url": f"/api/v1/exports/{name}"}


@router.get("/{filename}")
def download(filename: str, _: User = Depends(get_current_user)) -> FileResponse:
    path = resolve_export_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp xuất.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        headers={"Cache-Control": "private, no-store", "Pragma": "no-cache"},
    )
