"""Keep old files until commit; remove newly staged copies after rollback/close.

A process crash can leave an unreferenced copy, but never deletes the copy still
referenced by a rolled-back database transaction. Original uploads are retained.
"""

import logging
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
_KEY = "reviewed_file_changes"


def stage_file_change(db: Session, *, created: Path | None = None, obsolete: Path | None = None):
    if not db.in_transaction():
        db.begin()
    changes = db.info.setdefault(_KEY, {"created": set(), "obsolete": set()})
    if created:
        changes["created"].add(created)
    if obsolete:
        changes["obsolete"].add(obsolete)


def _cleanup(paths):
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.error("Không thể dọn bản sao ảnh kiểm duyệt; cần kiểm tra kho lưu trữ.")


@event.listens_for(Session, "after_commit")
def _after_commit(db):
    if db.in_nested_transaction():
        return
    changes = db.info.pop(_KEY, None)
    if changes:
        _cleanup(changes["obsolete"])


@event.listens_for(Session, "after_transaction_end")
def _after_transaction_end(db, transaction):
    if transaction.parent is not None:
        return
    changes = db.info.pop(_KEY, None)
    if changes:
        _cleanup(changes["created"])
