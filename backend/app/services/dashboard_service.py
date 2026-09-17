from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.batch import Batch
from app.models.image import ImageRecord
from app.models.processing_job import JobStatus, ProcessingJob

def statistics(db: Session) -> dict:
    batches = db.scalar(select(func.count()).select_from(Batch)) or 0
    images = db.scalar(select(func.count()).select_from(ImageRecord)) or 0
    jobs = dict(db.execute(select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)).all())
    return {"batches": batches, "images": images, "jobs": {status: int(jobs.get(status, 0)) for status in JobStatus}}
