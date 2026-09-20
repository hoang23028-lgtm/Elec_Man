from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.security.dependencies import AuthContext, get_current_user, require_csrf
from app.security.rate_limit import login_account_rate_limiter, login_ip_rate_limiter
from app.services.auth_service import authenticate, logout

router = APIRouter()


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> LoginResponse:
    ip_key = _ip(request) or "unknown"
    account_key = f"{ip_key}:{payload.username.casefold()}"
    if not login_ip_rate_limiter.allowed(ip_key) or not login_account_rate_limiter.allowed(
        account_key
    ):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Có quá nhiều lần đăng nhập. Vui lòng thử lại sau.",
        )
    try:
        session_token, csrf_token, expires_at = authenticate(
            db, payload.username, payload.password, _ip(request), request.headers.get("user-agent")
        )
    except Exception:
        login_ip_rate_limiter.record_failure(ip_key)
        login_account_rate_limiter.record_failure(account_key)
        raise
    login_account_rate_limiter.reset(account_key)
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_route(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
) -> Response:
    settings = get_settings()
    logout(db, auth.session, _ip(request))
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, username=user.username, last_login_at=user.last_login_at)
