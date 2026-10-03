from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.audit_log import AuditLog
from app.models.training_run import TrainingRun
from app.services import training_service as service


def _database(monkeypatch, count=37):
    db = MagicMock()
    db.scalar.return_value = None
    monkeypatch.setattr(
        service,
        "dataset_summary",
        lambda *_: SimpleNamespace(
            eligible_samples=count,
            minimum_samples=200,
            ready=count >= 200,
            new_samples_since_last_run=count,
            auto_start_enabled=True,
        ),
    )
    monkeypatch.setattr(service, "_row", lambda record: record)

    def assign_id(record):
        if isinstance(record, TrainingRun):
            record.id = uuid4()

    db.add.side_effect = assign_id
    return db


def test_standard_training_still_requires_configured_threshold(monkeypatch):
    db = _database(monkeypatch)
    with pytest.raises(HTTPException) as error:
        service.enqueue_training(db, "MANUAL", None)
    assert error.value.status_code == 422
    db.commit.assert_not_called()


def test_manual_experiment_is_audited_without_changing_settings(monkeypatch):
    db = _database(monkeypatch)
    run = service.enqueue_training(db, "MANUAL", None, experimental=True)
    assert run.sample_count == 37
    assert run.status == "PENDING"
    assert run.metrics_json["configured_minimum_samples"] == 200
    assert run.metrics_json["experimental"] is True
    assert run.metrics_json["below_configured_minimum"] is True
    added = [call.args[0] for call in db.add.call_args_list]
    assert all(isinstance(record, TrainingRun | AuditLog) for record in added)
    assert added[-1].details_json["experimental"] is True
    db.commit.assert_called_once()


def test_auto_training_cannot_use_experimental_override(monkeypatch):
    db = _database(monkeypatch)
    with pytest.raises(ValueError):
        service.enqueue_training(db, "AUTO", None, experimental=True)
    db.commit.assert_not_called()


def test_experiment_still_needs_train_and_validation_samples(monkeypatch):
    db = _database(monkeypatch, count=2)
    with pytest.raises(HTTPException):
        service.enqueue_training(db, "MANUAL", None, experimental=True)
    db.commit.assert_not_called()
