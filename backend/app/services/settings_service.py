from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.settings import SettingRow

RULES: dict[str, tuple[type, float, float]] = {
    "confidence_ok_threshold": (float, 0.0, 1.0),
    "confidence_review_threshold": (float, 0.0, 1.0),
    "max_upload_size_mb": (int, 1, 100),
    "max_retry_count": (int, 1, 10),
    "data_retention_days": (int, 1, 3650),
    "worker_poll_interval_seconds": (float, 0.1, 60.0),
    "electricity_unit_price_vnd": (int, 1, 1_000_000),
    "training_auto_start": (int, 0, 1),
    "training_min_samples": (int, 2, 100_000),
    "training_min_new_samples": (int, 1, 100_000),
}


def _audit_target(keys: list[str]) -> str:
    """Keep the audit target within the database column limit.

    The full key/value changes are retained in ``details_json``.
    """
    joined = ",".join(sorted(keys))
    return joined if len(joined) <= 64 else f"bulk:{len(keys)} settings"


def list_settings(db: Session) -> list[SettingRow]:
    records = db.scalars(select(SystemSetting).order_by(SystemSetting.key)).all()
    return [
        SettingRow(
            key=record.key,
            value=record.value_json,
            description=record.description,
            updated_at=record.updated_at,
        )
        for record in records
    ]


def _validated_value(key: str, value: Any) -> int | float:
    if key not in RULES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Cấu hình không xác định: {key}",
        )
    expected_type, minimum, maximum = RULES[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Giá trị không hợp lệ cho {key}",
        )
    converted = expected_type(value)
    if not minimum <= converted <= maximum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Giá trị nằm ngoài phạm vi cho phép của {key}",
        )
    return converted


def update_settings(
    db: Session, values: dict[str, Any], user: User, ip_address: str | None
) -> list[SettingRow]:
    validated = {key: _validated_value(key, value) for key, value in values.items()}
    if "confidence_ok_threshold" in validated or "confidence_review_threshold" in validated:
        current = {
            record.key: record.value_json for record in db.scalars(select(SystemSetting)).all()
        }
        current.update(validated)
        if current["confidence_review_threshold"] > current["confidence_ok_threshold"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ngưỡng cần kiểm duyệt không được lớn hơn ngưỡng đạt yêu cầu.",
            )
    changes: dict[str, dict[str, Any]] = {}
    for key, value in validated.items():
        record = db.get(SystemSetting, key)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy cấu hình: {key}",
            )
        changes[key] = {"old": record.value_json, "new": value}
        record.value_json = value
        record.updated_by = user.id
    db.add(
        AuditLog(
            user_id=user.id,
            action="CHANGE_SETTING",
            target_type="system_settings",
            target_id=_audit_target(list(validated)),
            details_json=changes,
            ip_address=ip_address,
        )
    )
    db.commit()
    return list_settings(db)
