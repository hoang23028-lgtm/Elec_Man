from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.security.dependencies import get_current_user, require_csrf
from app.services.export_service import create_final_exports, resolve_export_path

router = APIRouter()


@router.post("/final", dependencies=[Depends(require_csrf)])
def export_final(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    bundle = create_final_exports(db)
    db.add(
        AuditLog(
            user_id=user.id,
            action="EXPORT_RECONCILIATION_REPORT",
            target_type="export",
            target_id=bundle.excel_name,
            details_json={
                "excel_filename": bundle.excel_name,
                "json_filename": bundle.json_name,
                "exported_rows": bundle.row_count,
            },
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    return {
        "excel_filename": bundle.excel_name,
        "excel_download_url": f"/api/v1/exports/{bundle.excel_name}",
        "json_filename": bundle.json_name,
        "json_download_url": f"/api/v1/exports/{bundle.json_name}",
        "exported_rows": bundle.row_count,
    }


@router.get("/{filename}")
def download(filename: str, _: User = Depends(get_current_user)) -> FileResponse:
    path = resolve_export_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp xuất.")
    media_type = (
        "application/json; charset=utf-8"
        if path.suffix == ".json"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        headers={"Cache-Control": "private, no-store", "Pragma": "no-cache"},
    )
