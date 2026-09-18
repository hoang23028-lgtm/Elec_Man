from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.security.dependencies import get_current_user, require_csrf
from app.security.rate_limit import login_rate_limiter
from app.services.auth_service import authenticate, logout

router = APIRouter()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> LoginResponse:
    key = f"{_ip(request)}:{payload.username.casefold()}"
    if not login_rate_limiter.allowed(key):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )
    try:
        session_token, csrf_token, expires_at = authenticate(
            db, payload.username, payload.password, _ip(request), request.headers.get("user-agent")
        )
    except Exception:
        login_rate_limiter.record_failure(key)
        raise
    login_rate_limiter.reset(key)
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return LoginResponse(csrf_token=csrf_token, expires_at=expires_at)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
def logout_route(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    settings = get_settings()
    logout(db, request.cookies.get(settings.session_cookie_name), _ip(request))
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, username=user.username, last_login_at=user.last_login_at)
