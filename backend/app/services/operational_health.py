"""Bounded aggregate diagnostics; no customer data, credentials or error traces."""

import json
import shutil
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.ai_result import AiResult
from app.models.processing_job import ProcessingJob
from app.models.training_run import TrainingRun
from app.services.performance_profile import summarize_timings


def health_overview(db):
    settings = get_settings()
    now = datetime.now(UTC)
    counts = dict(
        db.execute(select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)).all()
    )
    oldest = db.scalar(
        select(func.min(ProcessingJob.created_at)).where(ProcessingJob.status == "PENDING")
    )
    stuck = (
        db.scalar(
            select(func.count())
            .select_from(ProcessingJob)
            .where(
                ProcessingJob.status == "PROCESSING",
                ProcessingJob.started_at
                < now - timedelta(seconds=settings.job_stuck_timeout_seconds),
            )
        )
        or 0
    )
    failed_today = (
        db.scalar(
            select(func.count())
            .select_from(ProcessingJob)
            .where(
                ProcessingJob.status == "FAILED",
                ProcessingJob.completed_at >= now - timedelta(hours=24),
            )
        )
        or 0
    )
    # Last 500 completed jobs: bounded payload/time, not all raw OCR results.
    durations = list(
        db.scalars(
            select(
                func.extract("epoch", ProcessingJob.completed_at - ProcessingJob.started_at) * 1000
            )
            .where(
                ProcessingJob.status == "COMPLETED",
                ProcessingJob.started_at.is_not(None),
                ProcessingJob.completed_at.is_not(None),
            )
            .order_by(ProcessingJob.completed_at.desc())
            .limit(500)
        )
    )
    durations = sorted(float(value) for value in durations if value is not None and value >= 0)
    stage_latency = summarize_timings(
        db.execute(
            select(
                AiResult.raw_result_json["timings_ms"],
                AiResult.raw_result_json["reading_only"],
                AiResult.raw_result_json["reader_diagnostics"]["candidates"],
            )
            .order_by(AiResult.created_at.desc())
            .limit(500)
        ).all()
    )
    run = db.scalar(select(TrainingRun).order_by(TrainingRun.created_at.desc()).limit(1))
    disks = {}
    for key, path in (("images", settings.storage_root), ("models", settings.models_root)):
        try:
            usage = shutil.disk_usage(path)
            disks[key] = {
                "free_bytes": usage.free,
                "total_bytes": usage.total,
                "free_percent": round(usage.free / usage.total * 100, 1),
            }
        except OSError:
            disks[key] = None
    backup = None
    try:
        raw = json.loads(
            (settings.storage_root / ".maintenance" / "backup-status.json").read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(raw, dict):
            raise ValueError("Invalid backup status")
        backup = {key: raw.get(key) for key in ("status", "completed_at", "verified", "error_code")}
    except (OSError, ValueError, TypeError):
        pass
    alerts = []
    if stuck:
        alerts.append({"severity": "error", "message": f"{stuck} tác vụ xử lý quá thời hạn."})
    if failed_today:
        alerts.append(
            {"severity": "warning", "message": f"{failed_today} tác vụ thất bại trong 24 giờ."}
        )
    if oldest and (now - oldest).total_seconds() > settings.job_stuck_timeout_seconds:
        alerts.append(
            {
                "severity": "warning",
                "message": "Hàng đợi đang chờ quá lâu. Kiểm tra worker và bộ đọc.",
            }
        )
    for key, usage in disks.items():
        if not usage or usage["free_percent"] < 10:
            alerts.append(
                {
                    "severity": "warning",
                    "message": f"Vùng {key} không khả dụng hoặc còn dưới 10% dung lượng.",
                }
            )
    if not backup or backup.get("verified") is not True:
        alerts.append(
            {
                "severity": "warning",
                "message": "Chưa ghi nhận sao lưu đã kiểm tra checksum. "
                "Cần cấu hình tác vụ sao lưu.",
            }
        )
    else:
        try:
            if now - datetime.fromisoformat(backup["completed_at"]) > timedelta(hours=26):
                alerts.append({"severity": "warning", "message": "Bản sao lưu đã quá 26 giờ."})
        except (TypeError, ValueError):
            alerts.append({"severity": "warning", "message": "Thời điểm sao lưu không hợp lệ."})
    return {
        "observed_at": now.isoformat(),
        "queue": counts,
        "stuck_jobs": stuck,
        "oldest_pending_seconds": round((now - oldest).total_seconds()) if oldest else None,
        "failed_last_24h": failed_today,
        "latency": {
            "samples": len(durations),
            "scope": "last_500_completed_jobs",
            "p50_ms": durations[int((len(durations) - 1) * 0.5)] if durations else None,
            "p95_ms": durations[int((len(durations) - 1) * 0.95)] if durations else None,
        },
        "training": {
            "status": run.status,
            "progress": run.progress,
            "stage": run.stage,
            "heartbeat_at": (run.metrics_json or {}).get("heartbeat_at"),
        }
        if run
        else None,
        "disks": disks,
        "stage_latency": stage_latency,
        "backup": backup,
        "alerts": alerts,
        "note": "Trạng thái hàng đợi không thay thế heartbeat của worker; "
        "độ trễ bao gồm toàn tác vụ, không chỉ suy luận AI.",
    }
