from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.models.system_setting import SystemSetting
from app.models.training_run import TrainingRun
from app.models.user import User
from app.schemas.training import DatasetSummary, TrainingOverview, TrainingRunRow


def _setting(db: Session, key: str, default: int) -> int:
    record = db.get(SystemSetting, key)
    return int(record.value_json) if record is not None else default


def eligible_clause():
    return (
        MeterReading.review_status == "CONFIRMED",
        MeterReading.reviewed_by.is_not(None),
        MeterReading.final_customer_id.is_not(None),
        MeterReading.final_meter_reading.is_not(None),
    )


def _row(run: TrainingRun) -> TrainingRunRow:
    return TrainingRunRow(
        id=run.id,
        status=run.status,
        trigger=run.trigger,
        stage=run.stage,
        progress=run.progress,
        sample_count=run.sample_count,
        training_count=run.training_count,
        validation_count=run.validation_count,
        dataset_hash=run.dataset_hash,
        metrics=run.metrics_json,
        error_message=run.error_message,
        model_id=run.model_id,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def dataset_summary(db: Session) -> DatasetSummary:
    uploaded = int(db.scalar(select(func.count(ImageRecord.id))) or 0)
    confirmed = int(
        db.scalar(
            select(func.count(MeterReading.id)).where(MeterReading.review_status == "CONFIRMED")
        )
        or 0
    )
    eligible = int(
        db.scalar(
            select(func.count(func.distinct(ImageRecord.sha256)))
            .join(MeterReading, MeterReading.image_id == ImageRecord.id)
            .where(*eligible_clause())
        )
        or 0
    )
    last_count = int(
        db.scalar(
            select(TrainingRun.sample_count)
            .where(TrainingRun.status == "COMPLETED")
            .order_by(TrainingRun.completed_at.desc())
            .limit(1)
        )
        or 0
    )
    minimum = _setting(db, "training_min_samples", 20)
    new_samples = max(0, eligible - last_count)
    return DatasetSummary(
        uploaded_images=uploaded,
        confirmed_images=confirmed,
        eligible_samples=eligible,
        minimum_samples=minimum,
        new_samples_since_last_run=new_samples,
        auto_start_enabled=bool(_setting(db, "training_auto_start", 1)),
        ready=eligible >= minimum,
    )


def overview(db: Session) -> TrainingOverview:
    runs = db.scalars(select(TrainingRun).order_by(TrainingRun.created_at.desc()).limit(20)).all()
    return TrainingOverview(dataset=dataset_summary(db), runs=[_row(run) for run in runs])


def enqueue_training(
    db: Session, trigger: str, user: User | None, ip_address: str | None = None
) -> TrainingRunRow:
    active = db.scalar(
        select(TrainingRun).where(TrainingRun.status.in_(("PENDING", "RUNNING"))).limit(1)
    )
    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Đã có một phiên huấn luyện đang chờ hoặc đang chạy.",
        )
    summary = dataset_summary(db)
    if not summary.ready:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Cần tối thiểu {summary.minimum_samples} ảnh đã được con người xác nhận; "
                f"hiện có {summary.eligible_samples}."
            ),
        )
    run = TrainingRun(
        status="PENDING",
        trigger=trigger,
        stage="QUEUED",
        progress=0,
        sample_count=summary.eligible_samples,
        created_at=datetime.now(UTC),
        requested_by=user.id if user else None,
    )
    db.add(run)
    db.flush()
    if user is not None:
        db.add(
            AuditLog(
                user_id=user.id,
                action="START_TRAINING",
                target_type="training_run",
                target_id=str(run.id),
                details_json={"sample_count": run.sample_count},
                ip_address=ip_address,
            )
        )
    db.commit()
    db.refresh(run)
    return _row(run)


def maybe_enqueue_auto(db: Session) -> bool:
    summary = dataset_summary(db)
    minimum_new = _setting(db, "training_min_new_samples", 10)
    if (
        not summary.auto_start_enabled
        or not summary.ready
        or summary.new_samples_since_last_run < minimum_new
    ):
        return False
    if db.scalar(
        select(TrainingRun.id).where(TrainingRun.status.in_(("PENDING", "RUNNING"))).limit(1)
    ):
        return False
    enqueue_training(db, "AUTO", None)
    return True
