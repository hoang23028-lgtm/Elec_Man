from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models.audit_log import AuditLog
from app.models.dataset_annotation import DatasetAnnotation
from app.models.image import ImageRecord
from app.models.meter_reading import MeterReading
from app.schemas.dataset import DatasetAnnotationRequest
from app.services.dataset_policy import base_eligible, make_manifest, sample_issues

DATASET_LOCK = 73051029


def lock_dataset(db):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": DATASET_LOCK})


def serialize_record(record):
    if record is None:
        return {}
    result = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name)
        if isinstance(value, datetime | date):
            value = value.isoformat()
        elif isinstance(value, UUID | Decimal):
            value = str(value)
        result[column.name] = value
    return result


def dataset_samples(db):
    records = db.execute(
        select(ImageRecord, MeterReading, DatasetAnnotation)
        .join(MeterReading, MeterReading.image_id == ImageRecord.id)
        .outerjoin(DatasetAnnotation, DatasetAnnotation.image_id == ImageRecord.id)
        .order_by(ImageRecord.sha256, ImageRecord.id)
    ).all()
    return [
        {
            "image": serialize_record(image),
            "reading": serialize_record(reading),
            "annotation": serialize_record(annotation),
        }
        for image, reading, annotation in records
    ]


def quality_summary(samples):
    summary = {
        "total": len(samples),
        "eligible": sum(base_eligible(s) for s in samples),
        "verified": sum(not sample_issues(s) for s in samples),
        "unverified_identity": sum(
            base_eligible(s)
            and not (s["annotation"].get("group_key") and s["annotation"].get("identity_verified"))
            for s in samples
        ),
        "stale_labels": sum(
            bool(s["annotation"].get("label_verified"))
            and s["annotation"].get("label_revision") != s["reading"].get("revision")
            for s in samples
        ),
        "train": 0,
        "validation": 0,
        "holdout": 0,
        "conflicts": [],
    }
    try:
        manifest = make_manifest(samples)
        summary.update({key.lower(): len(rows) for key, rows in manifest["partitions"].items()})
    except ValueError as error:
        summary["conflicts"] = [str(error)]
    return summary


def data_overview(db, offset=0, limit=12, search=""):
    samples = dataset_samples(db)
    query = search.strip().casefold()
    filtered = [
        s
        for s in samples
        if not query
        or query
        in " ".join(
            (
                s["image"]["original_filename"],
                s["reading"].get("final_customer_id") or "",
                s["annotation"].get("group_key") or "",
            )
        ).casefold()
    ]
    return {
        "summary": quality_summary(samples),
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "image_id": s["image"]["id"],
                "filename": s["image"]["original_filename"],
                "label": s["reading"].get("final_meter_reading"),
                "label_revision": s["reading"]["revision"],
                "annotation": s["annotation"],
                "issues": sample_issues(s),
                "review_status": s["reading"]["review_status"],
            }
            for s in filtered[offset : offset + limit]
        ],
    }


def save_annotation(db, image_id, payload: DatasetAnnotationRequest, user, ip_address=None):
    lock_dataset(db)
    reading = db.scalar(
        select(MeterReading).where(MeterReading.image_id == image_id).with_for_update()
    )
    if reading is None:
        raise HTTPException(404, "Ảnh chưa có kết quả/nhãn để chuẩn bị dữ liệu.")
    record = db.get(DatasetAnnotation, image_id)
    if payload.expected_label_revision != reading.revision or payload.expected_revision != (
        record.revision if record else 0
    ):
        raise HTTPException(409, "Nhãn hoặc phân tập đã thay đổi. Hãy tải bản mới trước khi lưu.")
    if (
        record
        and record.holdout_locked_at
        and (payload.partition != "HOLDOUT" or payload.group_key != record.group_key)
    ):
        raise HTTPException(
            422, "Ảnh holdout đã khóa không được chuyển lại sang tập học hoặc đổi nhóm."
        )
    before = serialize_record(record)
    if record is None:
        record = DatasetAnnotation(image_id=image_id, label_revision=reading.revision)
        db.add(record)
    for key, value in payload.model_dump(
        exclude={"expected_revision", "expected_label_revision"}
    ).items():
        setattr(record, key, value)
    record.label_revision = reading.revision
    record.updated_by = user.id
    record.updated_at = datetime.now(UTC)
    if record.partition == "HOLDOUT" and record.holdout_locked_at is None:
        record.holdout_locked_at = datetime.now(UTC)
    db.flush()
    try:
        make_manifest(dataset_samples(db))  # Refuse alias/hash/customer leakage across partitions.
    except ValueError as error:
        db.rollback()
        raise HTTPException(422, str(error)) from None
    after = serialize_record(record)
    db.add(
        AuditLog(
            user_id=user.id,
            action="DATASET_ANNOTATION_UPDATED",
            target_type="image",
            target_id=str(image_id),
            details_json={"before_values": before, "after_values": after},
            ip_address=ip_address,
        )
    )
    db.commit()
    return after
