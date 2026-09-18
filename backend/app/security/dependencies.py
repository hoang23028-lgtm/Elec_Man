from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.session import SessionRecord
from app.models.user import User
from app.security.tokens import hash_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    session = db.scalar(
        select(SessionRecord).where(SessionRecord.session_token_hash == hash_token(token))
    )
    if session is None or session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired."
        )
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return user


def require_csrf(request: Request, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(get_settings().session_cookie_name)
    csrf_token = request.headers.get("X-CSRF-Token")
    if not token or not csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    session = db.scalar(
        select(SessionRecord).where(SessionRecord.session_token_hash == hash_token(token))
    )
    if session is None or session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired."
        )
    if hash_token(csrf_token) != session.csrf_token_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
