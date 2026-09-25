from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.security.passwords import verify_password
from app.services.auth_service import register_account


def _registration_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    AuditLog.__table__.create(engine)
    return engine


def test_registration_creates_inactive_argon2_account() -> None:
    engine = _registration_database()

    with Session(engine) as db:
        register_account(db, "pending.user", "a-secure-password", "127.0.0.1")
        user = db.scalar(select(User).where(User.username == "pending.user"))
        audit = db.scalar(select(AuditLog).where(AuditLog.action == "REGISTRATION_REQUESTED"))

    assert user is not None
    assert user.is_active is False
    assert verify_password(user.password_hash, "a-secure-password") is True
    assert audit is not None
    assert audit.details_json["result"] == "PENDING_ADMIN_APPROVAL"


def test_duplicate_registration_does_not_create_another_account() -> None:
    engine = _registration_database()

    with Session(engine) as db:
        register_account(db, "pending.user", "a-secure-password", "127.0.0.1")
        register_account(db, "PENDING.USER", "another-secure-password", "127.0.0.1")
        user_count = db.scalar(select(func.count(User.id)))
        ignored_count = db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == "REGISTRATION_REQUEST_IGNORED")
        )

    assert user_count == 1
    assert ignored_count == 1
