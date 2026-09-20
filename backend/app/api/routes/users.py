from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.pagination import validate_pagination
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import PasswordUpdate, UserCreate, UserRow, UserUpdate
from app.security.dependencies import AuthContext, get_current_user, require_csrf
from app.services.user_service import (
    change_password,
    create_user,
    delete_user,
    list_users,
    update_user,
)

router = APIRouter()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=list[UserRow])
def get_users(
    response: Response,
    offset: int = 0,
    limit: int = 20,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[UserRow]:
    validate_pagination(offset, limit)
    normalized_search = search.strip()[:64] if search else None
    rows, total = list_users(db, offset, limit, normalized_search)
    response.headers["X-Total-Count"] = str(total)
    return rows


@router.post("", response_model=UserRow, status_code=status.HTTP_201_CREATED)
def create_user_route(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
) -> UserRow:
    return create_user(db, payload, auth.user, _ip(request))


@router.patch("/{user_id}", response_model=UserRow)
def update_user_route(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
) -> UserRow:
    return update_user(db, user_id, payload, auth.user, _ip(request))


@router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_route(
    user_id: UUID,
    payload: PasswordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
) -> Response:
    change_password(
        db,
        user_id,
        payload.new_password,
        auth.user,
        auth.session.id,
        _ip(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_route(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
) -> Response:
    delete_user(db, user_id, auth.user, _ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
