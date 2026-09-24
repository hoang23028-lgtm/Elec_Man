from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.pagination import validate_pagination
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.customer import CustomerImportResponse, CustomerRow, CustomerSummary
from app.security.dependencies import get_current_user, require_csrf
from app.services.customer_service import (
    customer_summary,
    import_customers,
    list_customers,
    parse_customer_json,
)

router = APIRouter()
MAX_CUSTOMER_FILE_BYTES = 10 * 1024 * 1024


@router.get("/summary", response_model=CustomerSummary)
def get_customer_summary(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> CustomerSummary:
    return customer_summary(db)


@router.get("", response_model=list[CustomerRow])
def get_customers(
    response: Response,
    offset: int = 0,
    limit: int = 20,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CustomerRow]:
    validate_pagination(offset, limit)
    normalized_search = search.strip()[:255] if search else None
    rows, total = list_customers(db, offset, limit, normalized_search)
    response.headers["X-Total-Count"] = str(total)
    return rows


@router.post(
    "/import",
    response_model=CustomerImportResponse,
    dependencies=[Depends(require_csrf)],
)
async def import_customer_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CustomerImportResponse:
    filename = file.filename or ""
    if not filename.lower().endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Chỉ chấp nhận tệp JSON.",
        )
    content = await file.read(MAX_CUSTOMER_FILE_BYTES + 1)
    if len(content) > MAX_CUSTOMER_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Tệp dữ liệu khách hàng không được vượt quá 10 MB.",
        )
    try:
        result = import_customers(db, parse_customer_json(content))
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dữ liệu trùng mã khách hàng hoặc số serial công tơ.",
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    db.add(
        AuditLog(
            user_id=user.id,
            action="IMPORT_CUSTOMERS",
            target_type="customer",
            target_id=filename[:64],
            details_json={
                "filename": filename,
                "total": result.total,
                "created": result.created,
                "updated": result.updated,
                "reconciled_readings": result.reconciled_readings,
            },
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    return result
