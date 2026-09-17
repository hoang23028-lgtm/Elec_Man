from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.security.dependencies import get_current_user, require_csrf
from app.services.export_service import create_final_export
router = APIRouter()
@router.post("/final", dependencies=[Depends(require_csrf)])
def export_final(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    name, _ = create_final_export(db); db.add(AuditLog(user_id=user.id, action="EXPORT_EXCEL", target_type="export", target_id=name, details_json={}, ip_address=request.client.host if request.client else None)); db.commit(); return {"filename": name, "download_url": f"/api/v1/exports/{name}"}
@router.get("/{filename}")
def download(filename: str, _: User = Depends(get_current_user)) -> FileResponse:
    if Path(filename).name != filename or not filename.endswith(".xlsx"): raise HTTPException(status_code=404, detail="Export not found.")
    matches = list((get_settings().storage_root / "exports").rglob(filename))
    if len(matches) != 1 or not matches[0].is_file(): raise HTTPException(status_code=404, detail="Export not found.")
    return FileResponse(matches[0], media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)
