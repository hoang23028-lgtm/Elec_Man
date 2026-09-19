from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditRow


def list_audit_logs(
    db: Session, offset: int, limit: int, action: str | None
) -> tuple[list[AuditRow], int]:
    statement = (
        select(
            AuditLog,
            User.username,
            func.count(AuditLog.id).over().label("total_count"),
        )
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if action:
        statement = statement.where(AuditLog.action == action)
    rows = db.execute(statement).all()
    items = [
        AuditRow(
            id=record.id,
            username=username,
            action=record.action,
            target_type=record.target_type,
            target_id=record.target_id,
            ip_address=record.ip_address,
            created_at=record.created_at,
        )
        for record, username, _ in rows
    ]
    total = int(rows[0].total_count) if rows else 0
    if not rows and offset:
        count_statement = select(func.count(AuditLog.id))
        if action:
            count_statement = count_statement.where(AuditLog.action == action)
        total = int(db.scalar(count_statement) or 0)
    return items, total
