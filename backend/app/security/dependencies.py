from dataclasses import dataclass
from datetime import UTC, datetime
from secrets import compare_digest

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.session import SessionRecord
from app.models.user import User
from app.security.tokens import hash_token


@dataclass(frozen=True)
class AuthContext:
    session: SessionRecord
    user: User


def get_auth_context(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập.")
    record = db.execute(
        select(SessionRecord, User)
        .join(User, User.id == SessionRecord.user_id)
        .where(SessionRecord.session_token_hash == hash_token(token))
    ).one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        )
    session, user = record
    if session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        )
    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập.")
    return AuthContext(session=session, user=user)


def get_current_user(context: AuthContext = Depends(get_auth_context)) -> User:
    return context.user


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token or not compare_digest(
        hash_token(csrf_token), context.session.csrf_token_hash
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Xác thực CSRF thất bại.")
    return context
