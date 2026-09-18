from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.settings import SettingRow, SettingsUpdate
from app.security.dependencies import get_current_user, require_csrf
from app.services.settings_service import list_settings, update_settings

router = APIRouter()


@router.get("", response_model=list[SettingRow])
def get_settings_route(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[SettingRow]:
    return list_settings(db)


@router.patch("", response_model=list[SettingRow], dependencies=[Depends(require_csrf)])
def update_settings_route(
    payload: SettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SettingRow]:
    return update_settings(
        db, payload.values, user, request.client.host if request.client else None
    )
