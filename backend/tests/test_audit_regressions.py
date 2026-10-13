from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import settings_service as settings
from app.services import training_service as training


def test_minimum_two_is_rejected_and_legacy_policy_is_clamped():
    with pytest.raises(HTTPException) as error:
        settings._validated_value("training_min_samples", 2)
    assert error.value.status_code == 422
    db = MagicMock()
    db.execute.return_value.one.return_value = (2, 2, 2)
    db.scalar.return_value = 0
    summary = training.dataset_summary(
        db,
        {
            "training_min_samples": 2,
            "training_min_new_samples": 1,
            "training_auto_start": 1,
        },
    )
    assert summary.minimum_samples == 3
    assert not summary.ready


def test_auto_failure_never_enqueues_again():
    db = MagicMock()
    db.scalar.side_effect = [None, "FAILED", None, "FAILED"]
    summary = SimpleNamespace(auto_start_enabled=True, ready=True, new_samples_since_last_run=200)
    with (
        patch.object(training, "_training_settings", return_value={"training_min_new_samples": 25}),
        patch.object(training, "dataset_summary", return_value=summary),
        patch.object(training, "enqueue_training") as enqueue,
    ):
        assert training.maybe_enqueue_auto(db) is False
        assert training.maybe_enqueue_auto(db) is False
        enqueue.assert_not_called()


@pytest.mark.parametrize("latest, blocked", [("FAILED", True), ("COMPLETED", False), (None, False)])
def test_auto_failure_gate(latest, blocked):
    db = MagicMock()
    db.scalar.return_value = latest
    assert training._auto_failure_blocked(db) is blocked


def test_queue_lock_is_taken_before_active_check():
    db = MagicMock()
    db.get_bind.return_value.dialect.name = "postgresql"
    db.scalar.return_value = SimpleNamespace(status="RUNNING")
    with pytest.raises(HTTPException) as error:
        training.enqueue_training(db, "MANUAL", None)
    assert error.value.status_code == 409
    assert "pg_advisory_xact_lock" in str(db.execute.call_args.args[0])
    calls = [call[0] for call in db.mock_calls]
    assert calls.index("execute") < calls.index("scalar")
    db.add.assert_not_called()


def test_auto_rechecks_failure_inside_queue_lock():
    db = MagicMock()
    db.scalar.side_effect = [None, "FAILED"]
    with (
        patch.object(
            training,
            "dataset_summary",
            return_value=SimpleNamespace(
                auto_start_enabled=True, ready=True, new_samples_since_last_run=200
            ),
        ),
        pytest.raises(HTTPException) as error,
    ):
        training.enqueue_training(db, "AUTO", None)
    assert error.value.status_code == 409
    db.add.assert_not_called()


@pytest.mark.parametrize("key", list(settings.DEPLOYMENT_SETTINGS))
def test_deployment_settings_cannot_be_changed_through_api(key):
    db = MagicMock()
    with pytest.raises(HTTPException) as error:
        settings.update_settings(db, {key: 5}, SimpleNamespace(id=None), None)
    assert error.value.status_code == 422
    db.commit.assert_not_called()


def test_setting_list_reports_environment_not_obsolete_database_value():
    db = MagicMock()
    db.scalars.return_value.all.return_value = [
        SimpleNamespace(
            key="max_upload_size_mb",
            value_json=99,
            description="upload",
            updated_at=datetime.now(UTC),
        )
    ]
    with patch.object(settings, "get_settings", return_value=SimpleNamespace(max_image_size_mb=20)):
        row = settings.list_settings(db)[0]
    assert row.value == 20
    assert row.source == "deployment"
    assert row.editable is False
