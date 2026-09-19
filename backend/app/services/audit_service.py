from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditRow


def list_audit_logs(db: Session, offset: int, limit: int, action: str | None) -> list[AuditRow]:
    statement = (
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if action:
        statement = statement.where(AuditLog.action == action)
    return [
        AuditRow(
            id=record.id,
            username=username,
            action=record.action,
            target_type=record.target_type,
            target_id=record.target_id,
            ip_address=record.ip_address,
            created_at=record.created_at,
        )
        for record, username in db.execute(statement)
    ]


def count_audit_logs(db: Session, action: str | None) -> int:
    statement = select(func.count(AuditLog.id))
    if action:
        statement = statement.where(AuditLog.action == action)
    return int(db.scalar(statement) or 0)
