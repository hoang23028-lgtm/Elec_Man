from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.session import SessionRecord
from app.models.user import User
from app.security.passwords import hash_password, password_needs_rehash, verify_password
from app.security.tokens import generate_token, hash_token


def _audit(
    db: Session,
    action: str,
    ip_address: str | None,
    user_id: object | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target_type="user" if user_id else None,
            target_id=str(user_id) if user_id else None,
            details_json=details or {},
            ip_address=ip_address,
        )
    )


def authenticate(
    db: Session, username: str, password: str, ip_address: str | None, user_agent: str | None
) -> tuple[str, str, datetime]:
    user = db.scalar(select(User).where(User.username == username, User.deleted_at.is_(None)))
    password_hash = user.password_hash if user is not None and user.is_active else None
    password_valid = verify_password(password_hash, password)
    if user is None or not user.is_active or not password_valid:
        _audit(
            db,
            "LOGIN_FAILED",
            ip_address,
            details={"result": "DENIED", "reason": "invalid_credentials_or_inactive"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng.",
        )
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=get_settings().session_ttl_hours)
    raw_session = generate_token()
    raw_csrf = generate_token()
    db.add(
        SessionRecord(
            user_id=user.id,
            session_token_hash=hash_token(raw_session),
            csrf_token_hash=hash_token(raw_csrf),
            created_at=now,
            expires_at=expires_at,
            last_seen_at=now,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:1000],
        )
    )
    user.last_login_at = now
    _audit(
        db,
        "LOGIN_SUCCESS",
        ip_address,
        user.id,
        {"result": "SUCCESS", "session_expires_at": expires_at.isoformat()},
    )
    db.commit()
    return raw_session, raw_csrf, expires_at


def logout(db: Session, session: SessionRecord, ip_address: str | None) -> None:
    if session.revoked_at is not None:
        return
    session.revoked_at = datetime.now(UTC)
    _audit(
        db,
        "LOGOUT",
        ip_address,
        session.user_id,
        {"result": "SUCCESS", "session_id": str(session.id)},
    )
    db.commit()
