from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.session import SessionRecord
from app.models.user import User
from app.schemas.user import UserCreate, UserRow, UserUpdate
from app.security.passwords import hash_password


def _get_user(db: Session, user_id: UUID) -> User:
    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản.",
        )
    return user


def _active_user_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(User.id)).where(User.is_active.is_(True), User.deleted_at.is_(None))
        )
        or 0
    )


def _audit(
    db: Session,
    actor: User,
    action: str,
    target: User,
    ip_address: str | None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=actor.id,
            action=action,
            target_type="user",
            target_id=str(target.id),
            details_json={"username": target.username, **(details or {})},
            ip_address=ip_address,
        )
    )


def _commit_unique_username(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tên đăng nhập đã tồn tại.",
        ) from exc


def list_users(
    db: Session, offset: int, limit: int, search: str | None
) -> tuple[list[UserRow], int]:
    filters = [User.deleted_at.is_(None)]
    if search:
        filters.append(User.username.ilike(f"%{search}%"))
    statement = (
        select(User, func.count(User.id).over().label("total_count"))
        .where(*filters)
        .order_by(User.created_at.desc(), User.username)
        .offset(offset)
        .limit(limit)
    )
    rows = db.execute(statement).all()
    users = [UserRow.model_validate(user) for user, _ in rows]
    total = int(rows[0].total_count) if rows else 0
    if not rows and offset:
        total = int(db.scalar(select(func.count(User.id)).where(*filters)) or 0)
    return users, total


def create_user(db: Session, payload: UserCreate, actor: User, ip_address: str | None) -> UserRow:
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tên đăng nhập đã tồn tại.",
        ) from exc
    _audit(db, actor, "USER_CREATE", user, ip_address, {"is_active": user.is_active})
    _commit_unique_username(db)
    db.refresh(user)
    return UserRow.model_validate(user)


def update_user(
    db: Session,
    user_id: UUID,
    payload: UserUpdate,
    actor: User,
    ip_address: str | None,
) -> UserRow:
    user = _get_user(db, user_id)
    if payload.is_active is False:
        if user.id == actor.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể tự khóa tài khoản đang đăng nhập.",
            )
        if user.is_active and _active_user_count(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phải duy trì ít nhất một tài khoản đang hoạt động.",
            )
    changes: dict[str, dict[str, object]] = {}
    if payload.username is not None and payload.username != user.username:
        changes["username"] = {"old": user.username, "new": payload.username}
        user.username = payload.username
    if payload.is_active is not None and payload.is_active != user.is_active:
        changes["is_active"] = {"old": user.is_active, "new": payload.is_active}
        user.is_active = payload.is_active
        if not user.is_active:
            _revoke_sessions(db, user.id)
    if changes:
        _audit(db, actor, "USER_UPDATE", user, ip_address, changes)
    _commit_unique_username(db)
    db.refresh(user)
    return UserRow.model_validate(user)


def change_password(
    db: Session,
    user_id: UUID,
    new_password: str,
    actor: User,
    current_session_id: UUID,
    ip_address: str | None,
) -> None:
    user = _get_user(db, user_id)
    user.password_hash = hash_password(new_password)
    _revoke_sessions(db, user.id, current_session_id if user.id == actor.id else None)
    _audit(db, actor, "USER_PASSWORD_CHANGE", user, ip_address)
    db.commit()


def delete_user(db: Session, user_id: UUID, actor: User, ip_address: str | None) -> None:
    user = _get_user(db, user_id)
    if user.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể tự xóa tài khoản đang đăng nhập.",
        )
    if user.is_active and _active_user_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phải duy trì ít nhất một tài khoản đang hoạt động.",
        )
    user.is_active = False
    user.deleted_at = datetime.now(UTC)
    _revoke_sessions(db, user.id)
    _audit(db, actor, "USER_DELETE", user, ip_address)
    db.commit()


def _revoke_sessions(db: Session, user_id: UUID, except_session_id: UUID | None = None) -> None:
    statement = update(SessionRecord).where(
        SessionRecord.user_id == user_id, SessionRecord.revoked_at.is_(None)
    )
    if except_session_id is not None:
        statement = statement.where(SessionRecord.id != except_session_id)
    db.execute(statement.values(revoked_at=datetime.now(UTC)))
