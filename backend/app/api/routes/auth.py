from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    RegistrationRequest,
    RegistrationResponse,
)
from app.security.dependencies import AuthContext, get_current_user, require_csrf
from app.security.rate_limit import (
    login_account_rate_limiter,
    login_ip_rate_limiter,
    registration_ip_rate_limiter,
)
from app.services.auth_service import REGISTRATION_MESSAGE, authenticate, logout, register_account

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
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Có quá nhiều lần đăng nhập. Vui lòng thử lại sau.",
            headers={"Retry-After": "900"},
        )
    try:
        session_token, csrf_token, expires_at = authenticate(
            db, payload.username, payload.password, _ip(request), request.headers.get("user-agent")
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
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
        expires=expires_at,
        path="/",
    )
    return LoginResponse(csrf_token=csrf_token, expires_at=expires_at)


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def register(
    payload: RegistrationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegistrationResponse:
    ip_address = _ip(request)
    ip_key = ip_address or "unknown"
    if not registration_ip_rate_limiter.allowed(ip_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Có quá nhiều yêu cầu đăng ký. Vui lòng thử lại sau.",
            headers={"Retry-After": "3600"},
        )
    registration_ip_rate_limiter.record_failure(ip_key)
    register_account(db, payload.username, payload.password, ip_address)
    return RegistrationResponse(message=REGISTRATION_MESSAGE)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_route(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_csrf),
) -> Response:
    settings = get_settings()
    logout(db, auth.session, _ip(request))
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.app_env == "production",
        httponly=True,
        samesite="strict",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, username=user.username, last_login_at=user.last_login_at)
