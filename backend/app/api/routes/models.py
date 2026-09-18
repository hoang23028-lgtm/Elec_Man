from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.model_registry import ModelCreate, ModelRow
from app.security.dependencies import get_current_user, require_csrf
from app.services.model_registry_service import activate_model, list_models, register_model

router = APIRouter()


@router.get("", response_model=list[ModelRow])
def get_models(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[ModelRow]:
    return list_models(db)


@router.post(
    "",
    response_model=ModelRow,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_model(
    payload: ModelCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ModelRow:
    return register_model(db, payload, user, request.client.host if request.client else None)


@router.put(
    "/{model_id}/activate",
    response_model=ModelRow,
    dependencies=[Depends(require_csrf)],
)
def activate_model_route(
    model_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ModelRow:
    return activate_model(db, model_id, user, request.client.host if request.client else None)
