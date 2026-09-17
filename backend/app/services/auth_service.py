from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.session import SessionRecord
from app.models.user import User
from app.security.passwords import verify_password
from app.security.tokens import generate_token, hash_token


def _audit(db: Session, action: str, ip_address: str | None, user_id: object | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, target_type="user" if user_id else None, target_id=str(user_id) if user_id else None, details_json={}, ip_address=ip_address))


def authenticate(db: Session, username: str, password: str, ip_address: str | None, user_agent: str | None) -> tuple[str, str, datetime]:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active or not verify_password(user.password_hash, password):
        _audit(db, "LOGIN_FAILED", ip_address)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=get_settings().session_ttl_hours)
    raw_session = generate_token()
    raw_csrf = generate_token()
    db.add(SessionRecord(user_id=user.id, session_token_hash=hash_token(raw_session), csrf_token_hash=hash_token(raw_csrf), created_at=now, expires_at=expires_at, last_seen_at=now, ip_address=ip_address, user_agent=(user_agent or "")[:1000]))
    user.last_login_at = now
    _audit(db, "LOGIN_SUCCESS", ip_address, user.id)
    db.commit()
    return raw_session, raw_csrf, expires_at


def logout(db: Session, session_token: str | None, ip_address: str | None) -> None:
    if not session_token:
        return
    session = db.scalar(select(SessionRecord).where(SessionRecord.session_token_hash == hash_token(session_token)))
    if session is None or session.revoked_at is not None:
        return
    session.revoked_at = datetime.now(UTC)
    _audit(db, "LOGOUT", ip_address, session.user_id)
    db.commit()
