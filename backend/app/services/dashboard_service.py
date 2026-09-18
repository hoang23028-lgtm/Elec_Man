from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.image import ImageRecord
from app.models.processing_job import JobStatus, ProcessingJob


def statistics(db: Session) -> dict:
    """Return all dashboard counters with one database round trip."""
    statement = select(
        select(func.count(Batch.id)).scalar_subquery().label("batches"),
        select(func.count(ImageRecord.id)).scalar_subquery().label("images"),
        *[
            func.count(ProcessingJob.id)
            .filter(ProcessingJob.status == job_status)
            .label(job_status.value.lower())
            for job_status in JobStatus
        ],
    ).select_from(ProcessingJob)
    row = db.execute(statement).one()
    return {
        "batches": int(row.batches),
        "images": int(row.images),
        "jobs": {
            job_status: int(getattr(row, job_status.value.lower())) for job_status in JobStatus
        },
    }
