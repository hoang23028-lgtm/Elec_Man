from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import cv2
import numpy as np
import pytest
from app.models.model_registry import ModelRecord
from app.services.dataset_policy import make_manifest

from ai.training import trainer

POLYGON = {
    "points": [
        {"x": x, "y": y} for x, y in ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9))
    ]
}


def fixture_run(tmp_path):
    rows = []
    for index, partition in enumerate(("TRAIN", "TRAIN", "VALIDATION")):
        path = tmp_path / f"synthetic-{index}.png"
        assert cv2.imwrite(
            str(path), np.full((120, 240, 3), 100 + index * 10, np.uint8)
        )
        rows.append(
            {
                "image": {
                    "id": str(uuid4()),
                    "sha256": sha256(path.read_bytes()).hexdigest(),
                    "relative_path": path.name,
                },
                "reading": {
                    "revision": 1,
                    "review_status": "LABELED",
                    "reviewed_by": "actor",
                    "bbox_reviewed_by": "actor",
                    "meter_bbox_reviewed_by": "actor",
                    "final_meter_reading": "00120",
                    "reading_polygon_json": POLYGON,
                    "meter_polygon_json": POLYGON,
                },
                "annotation": {
                    "group_key": f"CT{index}",
                    "partition": partition,
                    "identity_verified": True,
                    "label_verified": True,
                    "label_revision": 1,
                },
            }
        )
    return SimpleNamespace(
        status="RUNNING",
        metrics_json={
            "dataset_snapshot": make_manifest(rows),
            "training_options": {"fine_tune_reader": False},
        },
        id=uuid4(),
    )


def test_frozen_manifest_to_artifacts_has_verified_provenance_without_mutating_labels(
    tmp_path, monkeypatch
):
    run = fixture_run(tmp_path)
    db = MagicMock()
    db.get.return_value = db.scalar.return_value = run
    session = MagicMock()
    session.__enter__.return_value = db
    monkeypatch.setattr(trainer, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        trainer,
        "get_settings",
        lambda: SimpleNamespace(
            storage_root=tmp_path,
            models_root=tmp_path / "models",
            training_timeout_seconds=120,
        ),
    )
    monkeypatch.setattr(
        trainer,
        "_benchmark_sequence_reader",
        lambda *a: {
            "exact_accuracy": None,
            "coverage": None,
            "evaluation_complete": False,
        },
    )
    monkeypatch.setattr(
        trainer, "_end_to_end", lambda *a: {"evaluation_complete": False}
    )

    def assign(record):
        if isinstance(record, ModelRecord):
            record.id = uuid4()

    db.add.side_effect = assign
    trainer.train_run(run.id)
    assert run.status == "COMPLETED"
    assert run.training_count == 2 and run.validation_count == 1
    assert run.metrics_json["sequence_reader_fine_tuned"] is False
    assert run.metrics_json["end_to_end_evaluated"] is False
    assert run.metrics_json["independent_holdout"] is False
    assert len(run.metrics_json["artifact_ids"]) == 2
    assert len(run.metrics_json["artifact_sha256"]) == 2
    artifacts = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], ModelRecord)
    ]
    assert all(r.status == "TESTING" for r in artifacts)
    assert all((tmp_path / "models" / r.file_path).is_file() for r in artifacts)
    assert all(r.metrics_json["training_run_id"] == str(run.id) for r in artifacts)


def test_snapshot_checksum_mismatch_is_rejected_before_training(tmp_path, monkeypatch):
    run = fixture_run(tmp_path)
    run.metrics_json["dataset_snapshot"]["partitions"]["TRAIN"][0]["reading"][
        "final_meter_reading"
    ] = "99999"
    db = MagicMock()
    db.get.return_value = run
    session = MagicMock()
    session.__enter__.return_value = db
    monkeypatch.setattr(trainer, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        trainer,
        "get_settings",
        lambda: SimpleNamespace(storage_root=tmp_path, models_root=tmp_path / "models"),
    )
    with pytest.raises(ValueError, match="checksum"):
        trainer.train_run(run.id)
    assert not (tmp_path / "models").exists()
