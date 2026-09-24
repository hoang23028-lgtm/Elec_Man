"""Dedicated process that schedules and executes supervised training runs."""

import logging
import signal
import time
from datetime import UTC, datetime

from sqlalchemy import select

from ai.training.trainer import train_run
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.audit_log import AuditLog
from app.models.training_run import TrainingRun
from app.services.training_service import maybe_enqueue_auto

running = True


def _stop(_: int, __: object) -> None:
    global running
    running = False


def _claim():
    with SessionLocal() as db:
        run = db.scalar(
            select(TrainingRun)
            .where(TrainingRun.status == "PENDING")
            .order_by(TrainingRun.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if run is None:
            return None
        run.status = "RUNNING"
        run.stage = "PREPARING_DATASET"
        run.progress = 5
        run.started_at = datetime.now(UTC)
        run_id = run.id
        db.add(
            AuditLog(
                user_id=None,
                action="TRAINING_STARTED",
                target_type="training_run",
                target_id=str(run.id),
                details_json={
                    "trigger": run.trigger,
                    "sample_count": run.sample_count,
                    "stage": run.stage,
                    "progress": run.progress,
                },
                ip_address=None,
            )
        )
        db.commit()
        return run_id


def _recover_interrupted_runs() -> int:
    """Close runs left in RUNNING when the trainer process was interrupted."""
    with SessionLocal() as db:
        interrupted = db.scalars(
            select(TrainingRun).where(TrainingRun.status == "RUNNING")
        ).all()
        message = (
            "Tiến trình huấn luyện trước đó bị gián đoạn. "
            "Hãy khởi chạy lại phiên huấn luyện."
        )
        for run in interrupted:
            previous_stage = run.stage
            run.status = "FAILED"
            run.stage = "FAILED"
            run.error_message = message
            run.completed_at = datetime.now(UTC)
            db.add(
                AuditLog(
                    user_id=None,
                    action="TRAINING_FAILED",
                    target_type="training_run",
                    target_id=str(run.id),
                    details_json={
                        "reason": "trainer_interrupted",
                        "error_message": message,
                        "last_stage": previous_stage,
                        "progress": run.progress,
                    },
                    ip_address=None,
                )
            )
        db.commit()
        return len(interrupted)


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    recovered = _recover_interrupted_runs()
    if recovered:
        logger.warning(
            "training_runs_recovered",
            extra={"event": "training_runs_recovered", "count": recovered},
        )
    while running:
        run_id = None
        try:
            with SessionLocal() as db:
                maybe_enqueue_auto(db)
            run_id = _claim()
            if run_id is None:
                time.sleep(5)
                continue
            train_run(run_id)
            logger.info(
                "training_completed",
                extra={"event": "training_completed", "run_id": str(run_id)},
            )
        except Exception as exc:
            logger.exception(
                "training_failed",
                extra={
                    "event": "training_failed",
                    "run_id": str(run_id) if run_id else None,
                },
            )
            if run_id is not None:
                with SessionLocal() as db:
                    run = db.get(TrainingRun, run_id)
                    if run is not None:
                        previous_stage = run.stage
                        run.status = "FAILED"
                        run.stage = "FAILED"
                        safe_message = (
                            "Huấn luyện thất bại. Hãy dùng mã phiên huấn luyện "
                            "để tra cứu log máy chủ."
                        )
                        run.error_message = safe_message
                        run.completed_at = datetime.now(UTC)
                        db.add(
                            AuditLog(
                                user_id=None,
                                action="TRAINING_FAILED",
                                target_type="training_run",
                                target_id=str(run.id),
                                details_json={
                                    "error_type": type(exc).__name__,
                                    "error_message": safe_message,
                                    "last_stage": previous_stage,
                                    "progress": run.progress,
                                },
                                ip_address=None,
                            )
                        )
                        db.commit()
            time.sleep(5)


if __name__ == "__main__":
    main()
