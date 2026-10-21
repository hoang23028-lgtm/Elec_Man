"""Train separate meter/register locators and a supervised whole-string reader."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from time import perf_counter
from types import SimpleNamespace

import numpy as np
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.model_registry import ModelRecord
from app.models.training_run import TrainingRun
from sqlalchemy import select

from ai.pipeline.geometry import (
    normalized_bbox_polygon,
    perspective_crop,
    transform_polygon,
)
from ai.pipeline.meter_pipeline import MeterReadingPipeline
from ai.pipeline.preprocessing import load_prepared_image
from ai.pipeline.register import integer_register_strip
from ai.readers.consensus import ConsensusMeterReader
from ai.training.dataset import export_sequence_dataset
from ai.training.deep_locator import benchmark_locators, train_deep_locator
from ai.training.keypoint_regressor import (
    KeypointRegionRegressor,
    extract_region_features,
)
from ai.training.metrics import polygon_iou, reading_metrics
from ai.training.sequence_finetune import dataset_items, evaluate_reader, fine_tune


class TrainingCancelled(RuntimeError):
    pass


def _ensure_running(run_id):
    with SessionLocal() as db:
        state = db.scalar(select(TrainingRun.status).where(TrainingRun.id == run_id))
    if state != "RUNNING":
        raise TrainingCancelled("Phiên không còn ở trạng thái huấn luyện.")


def _set_stage(run_id, stage, progress, details=None):
    with SessionLocal() as db:
        run = db.scalar(
            select(TrainingRun).where(TrainingRun.id == run_id).with_for_update()
        )
        if run is None or run.status == "CANCELLED":
            raise TrainingCancelled("Phiên huấn luyện đã được hủy.")
        run.stage, run.progress = stage, progress
        run.metrics_json = {
            **run.metrics_json,
            "heartbeat_at": datetime.now(UTC).isoformat(),
        }
        if details:
            run.metrics_json = {**run.metrics_json, **details}
        db.add(
            AuditLog(
                user_id=None,
                action="TRAINING_STAGE_CHANGED",
                target_type="training_run",
                target_id=str(run_id),
                details_json={"stage": stage, "progress": progress, **(details or {})},
                ip_address=None,
            )
        )
        db.commit()


def _polygon(reading, prefix="reading"):
    return tuple(
        (float(p["x"]), float(p["y"]))
        for p in getattr(reading, f"{prefix}_polygon_json")["points"]
    )


def _source(root, image):
    path = (root / image.relative_path).resolve()
    if (
        not path.is_relative_to(root.resolve())
        or not path.is_file()
        or sha256(path.read_bytes()).hexdigest() != image.sha256
    ):
        raise ValueError("Ảnh trong snapshot đã thay đổi hoặc không khả dụng.")
    source = load_prepared_image(path)
    if source is None:
        raise ValueError("Không thể giải mã ảnh trong snapshot.")
    return source


def _region_metrics(rows, root, meter_model, region_model):
    region_error, meter_error, region_iou, meter_iou = [], [], [], []
    for image, reading in rows:
        source = _source(root, image)
        meter_target, target = _polygon(reading, "meter"), _polygon(reading)
        meter = meter_model.predict(source)
        conditional = region_model.predict(perspective_crop(source, meter_target))
        region = (
            transform_polygon(conditional[0], meter_target, inverse=True)
            if conditional
            else None
        )
        meter_error.append(
            float(np.mean(np.abs(np.asarray(meter[0]) - meter_target)))
            if meter
            else 1.0
        )
        region_error.append(
            float(np.mean(np.abs(np.asarray(region) - target))) if region else 1.0
        )
        meter_iou.append(polygon_iou(meter[0], meter_target) if meter else 0.0)
        region_iou.append(polygon_iou(region, target) if region else 0.0)
    return {
        "samples": len(rows),
        "meter_mean_error": float(np.mean(meter_error)) if rows else 1.0,
        "reading_mean_error": float(np.mean(region_error)) if rows else 1.0,
        "meter_mean_iou": float(np.mean(meter_iou)) if rows else 0.0,
        "reading_mean_iou": float(np.mean(region_iou)) if rows else 0.0,
        "scope": "reading_conditional_on_ground_truth_meter",
    }


def _benchmark_sequence_reader(rows, root):
    reader = ConsensusMeterReader()
    records = []
    unavailable = False
    try:
        for image, reading in rows:
            crop = integer_register_strip(
                perspective_crop(_source(root, image), _polygon(reading))
            )
            diagnostics = {}
            started = perf_counter()
            value, confidence = reader.read(
                crop,
                integer_digits=len(reading.final_meter_reading),
                diagnostics=diagnostics,
            )
            unavailable |= diagnostics.get("decision") == "reader_service_unavailable"
            records.append(
                {
                    "expected": reading.final_meter_reading,
                    "predicted": value,
                    "confidence": confidence,
                    "elapsed_ms": (perf_counter() - started) * 1000,
                }
            )
    finally:
        reader.close()
    return {
        **reading_metrics(records),
        "evaluation_complete": not unavailable and bool(records),
    }


def _end_to_end(rows, root, region_path, meter_path, parseq_model):
    pipeline = MeterReadingPipeline(
        region_model_path=region_path,
        meter_model_path=meter_path,
        parseq_model=parseq_model,
    )
    records, meter_ious, region_ious = [], [], []
    unavailable = False
    try:
        for image, reading in rows:
            prepared = _source(root, image)
            started = perf_counter()
            result = pipeline.process(root / image.relative_path)
            unavailable |= (
                result.get("reader_diagnostics", {}).get("decision")
                == "reader_service_unavailable"
            )
            records.append(
                {
                    "expected": reading.final_meter_reading,
                    "predicted": result.get("meter_reading_ai"),
                    "confidence": result.get("meter_confidence", 0),
                    "elapsed_ms": (perf_counter() - started) * 1000,
                }
            )
            regions = result.get("regions", {})
            height, width = prepared.shape[:2]

            def region_polygon(key):
                polygon = regions.get(f"{key}_polygon")
                box = regions.get(key)
                return polygon or (
                    normalized_bbox_polygon(
                        tuple(
                            v / scale
                            for v, scale in zip(
                                box, (width, height, width, height), strict=True
                            )
                        )
                    )
                    if box
                    else None
                )

            meter_polygon = region_polygon("meter")
            reading_polygon = region_polygon("reading")
            meter_ious.append(
                polygon_iou(meter_polygon, _polygon(reading, "meter"))
                if meter_polygon
                else 0.0
            )
            region_ious.append(
                polygon_iou(reading_polygon, _polygon(reading))
                if reading_polygon
                else 0.0
            )
    finally:
        pipeline.meter_reader.close()
    return {
        **reading_metrics(records),
        "meter_mean_iou": float(np.mean(meter_ious)) if rows else 0.0,
        "reading_mean_iou": float(np.mean(region_ious)) if rows else 0.0,
        "evaluation_complete": bool(rows) and not unavailable,
        "scope": "automatic_full_image_default_digit_count",
    }


def train_run(run_id):
    settings = get_settings()
    with SessionLocal() as db:
        run = db.get(TrainingRun, run_id)
        if run is None:
            raise ValueError("Không tìm thấy phiên huấn luyện.")
        metadata = dict(run.metrics_json or {})
    snapshot = metadata.get("dataset_snapshot")
    if not snapshot:
        raise ValueError("Phiên cũ không có snapshot dữ liệu. Hãy tạo phiên mới.")
    body = {k: v for k, v in snapshot.items() if k != "sha256"}
    if (
        sha256(
            json.dumps(
                body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode()
        ).hexdigest()
        != snapshot["sha256"]
    ):
        raise ValueError("Snapshot huấn luyện không khớp checksum.")
    splits = {
        key: [
            (SimpleNamespace(**s["image"]), SimpleNamespace(**s["reading"]))
            for s in rows
        ]
        for key, rows in snapshot["partitions"].items()
    }
    train, validation, holdout = (
        splits["TRAIN"],
        splits["VALIDATION"],
        splits["HOLDOUT"],
    )
    if len(train) < 2 or not validation:
        raise ValueError("Không đủ mẫu train/validation tách riêng.")
    version = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{str(run_id)[:8]}"
    options = metadata.get("training_options", {})
    _set_stage(run_id, "EXTRACTING_FEATURES", 15)
    full_features, region_features, meter_targets, region_targets = [], [], [], []
    for image, reading in train:
        source = _source(settings.storage_root, image)
        frame, register = _polygon(reading, "meter"), _polygon(reading)
        full_features.append(extract_region_features(source))
        region_features.append(extract_region_features(perspective_crop(source, frame)))
        meter_targets.append(np.asarray(frame))
        region_targets.append(np.asarray(transform_polygon(register, frame)))
    meter_model = KeypointRegionRegressor.train(full_features, meter_targets)
    region_model = KeypointRegionRegressor.train(
        region_features, region_targets
    ).in_meter_coordinates()
    _set_stage(run_id, "VALIDATING", 30)
    region_metrics = _region_metrics(
        validation, settings.storage_root, meter_model, region_model
    )
    meter_model = meter_model.with_validation_error(region_metrics["meter_mean_error"])
    region_model = region_model.with_validation_error(
        region_metrics["reading_mean_error"]
    )
    relative_paths = {
        "meter_locator_ridge": f"meter_locator_ridge/{version}/model.npz",
        "reading_region_ridge": f"reading_region_ridge/{version}/model.npz",
    }
    for kind, model in (
        ("meter_locator_ridge", meter_model),
        ("reading_region_ridge", region_model),
    ):
        path = settings.models_root / relative_paths[kind]
        path.parent.mkdir(parents=True, exist_ok=True)
        model.save(path)
    deep_metrics, deep_models = None, None
    if options.get("benchmark_deep_locator", False):
        _set_stage(run_id, "TRAINING_DEEP_LOCATORS", 34)

        def samples(rows, relative):
            for image, reading in rows:
                source = _source(settings.storage_root, image)
                frame = _polygon(reading, "meter")
                yield (
                    (
                        perspective_crop(source, frame),
                        transform_polygon(_polygon(reading), frame),
                    )
                    if relative
                    else (source, frame)
                )

        learned, summaries = [], {}
        for relative, kind in (
            (False, "meter_locator_mobilenetv3"),
            (True, "reading_region_mobilenetv3"),
        ):
            relative_paths[kind] = f"{kind}/{version}/model.onnx"
            model, summary = train_deep_locator(
                samples(train, relative),
                samples(validation, relative),
                settings.models_root / relative_paths[kind],
                coordinate_space="meter" if relative else "image",
                epochs=options.get("deep_locator_epochs", 40),
                checkpoint=lambda: _ensure_running(run_id),
                max_seconds=min(900, settings.training_timeout_seconds),
            )
            learned.append(model)
            summaries[kind] = summary
        deep_models = tuple(learned)
        deep_metrics = {
            "training": summaries,
            "validation": benchmark_locators(
                validation,
                settings.storage_root,
                meter_model,
                region_model,
                *deep_models,
                _source,
                _polygon,
            ),
            "holdout": benchmark_locators(
                holdout,
                settings.storage_root,
                meter_model,
                region_model,
                *deep_models,
                _source,
                _polygon,
            ),
        }
    _set_stage(run_id, "BUILDING_SEQUENCE_DATASET", 40)
    dataset_root = settings.models_root / "sequence_datasets" / version
    dataset = export_sequence_dataset(
        train, validation, settings.storage_root, dataset_root, holdout_rows=holdout
    )
    fine_metrics, trained_reader = None, None
    if options.get("fine_tune_reader", True):
        _set_stage(run_id, "FINE_TUNING_SEQUENCE_READER", 45)
        reader_relative = f"parseq_tiny_finetuned/{version}/model.safetensors"

        def progress(epoch, total, result):
            _set_stage(
                run_id,
                "FINE_TUNING_SEQUENCE_READER",
                45 + round(35 * epoch / total),
                {
                    "training_epoch": epoch,
                    "training_epochs": total,
                    "training_loss": result["loss"],
                },
            )

        trained_reader, fine_metrics = fine_tune(
            dataset_root,
            settings.models_root / reader_relative,
            options,
            progress,
            max_seconds=settings.training_timeout_seconds,
            checkpoint=lambda: _ensure_running(run_id),
        )
        relative_paths["parseq_tiny_finetuned"] = reader_relative
    _set_stage(run_id, "BENCHMARKING_SEQUENCE_READER", 82)
    baseline = _benchmark_sequence_reader(validation, settings.storage_root)
    _set_stage(run_id, "EVALUATING_HOLDOUT", 88)
    reader_holdout = (
        evaluate_reader(trained_reader, dataset_items(dataset_root, "holdout"))
        if trained_reader and holdout
        else None
    )
    parseq_model = (
        {
            "model_file": relative_paths["parseq_tiny_finetuned"],
            "model_sha256": fine_metrics["sha256"],
        }
        if fine_metrics
        else None
    )
    e2e = _end_to_end(
        holdout,
        settings.storage_root,
        settings.models_root / relative_paths["reading_region_ridge"],
        settings.models_root / relative_paths["meter_locator_ridge"],
        parseq_model,
    )
    deep_e2e = (
        _end_to_end(
            holdout,
            settings.storage_root,
            settings.models_root / relative_paths["reading_region_mobilenetv3"],
            settings.models_root / relative_paths["meter_locator_mobilenetv3"],
            parseq_model,
        )
        if deep_models
        else None
    )
    if deep_metrics:
        deep_metrics.update(
            ridge_end_to_end=e2e,
            mobilenetv3_end_to_end=deep_e2e,
            independent_holdout=snapshot["independent_holdout"],
            scope="same_frozen_snapshot_not_automatic_selection",
        )
    metrics = {
        **metadata,
        "training_run_id": str(run_id),
        "dataset_hash": snapshot["sha256"],
        "validation_scope": "ground_truth_crop_and_digit_count",
        "end_to_end_evaluated": e2e["evaluation_complete"],
        "independent_holdout": snapshot["independent_holdout"],
        "validation_groups_verified": snapshot["validation_groups_verified"],
        "unknown_meter_identity_samples": snapshot["unknown_meter_identity_samples"],
        "holdout_images": len(holdout),
        "validation_images": len(validation),
        "training_images": len(train),
        "coordinate_space": "meter",
        "sequence_reader_trainable": True,
        "sequence_reader_fine_tuned": bool(fine_metrics),
        "sequence_dataset": dataset,
        "sequence_fine_tune": fine_metrics,
        "sequence_baseline": baseline,
        "locator_benchmark": deep_metrics,
        "locator_family": "ridge",
        "holdout_reader": reader_holdout,
        "holdout_end_to_end": e2e,
        "validation_reading_exact_accuracy": fine_metrics["validation"][
            "exact_accuracy"
        ]
        if fine_metrics
        else baseline["exact_accuracy"],
        "sequence_reader_coverage": fine_metrics["validation"]["coverage"]
        if fine_metrics
        else baseline["coverage"],
        "sequence_reader_unavailable": not baseline["evaluation_complete"],
        "validation_region_accuracy": max(
            0.0, 1 - region_metrics["reading_mean_error"] * 4
        ),
        "validation_meter_region_accuracy": max(
            0.0, 1 - region_metrics["meter_mean_error"] * 4
        ),
        "validation_region_iou": region_metrics["reading_mean_iou"],
        "validation_meter_region_iou": region_metrics["meter_mean_iou"],
        "algorithm": "meter-relative-ridge-supervised-sequence-v2",
        "score_calibrated": False,
    }
    _set_stage(run_id, "REGISTERING_MODEL", 95)
    with SessionLocal() as db:
        run = db.scalar(
            select(TrainingRun).where(TrainingRun.id == run_id).with_for_update()
        )
        if run is None or run.status == "CANCELLED":
            raise TrainingCancelled()
        records = []
        for kind, relative in relative_paths.items():
            record = ModelRecord(
                model_name=kind,
                model_type=kind,
                version=version,
                file_path=relative,
                metrics_json={},
                status="TESTING",
                sha256=sha256(
                    (settings.models_root / relative).read_bytes()
                ).hexdigest(),
                created_at=datetime.now(UTC),
            )
            db.add(record)
            records.append(record)
        db.flush()
        metrics["artifact_ids"] = [str(r.id) for r in records]
        metrics["artifact_sha256"] = {str(r.id): r.sha256 for r in records}
        for record in records:
            record.metrics_json = dict(metrics)
            if record.model_type.endswith("mobilenetv3"):
                record.metrics_json.update(
                    locator_family="mobilenetv3",
                    holdout_end_to_end=deep_e2e,
                    end_to_end_evaluated=deep_e2e["evaluation_complete"],
                    validation_meter_region_accuracy=max(
                        0,
                        1
                        - deep_metrics["training"]["meter_locator_mobilenetv3"][
                            "validation_error"
                        ]
                        * 4,
                    ),
                    validation_region_accuracy=max(
                        0,
                        1
                        - deep_metrics["training"]["reading_region_mobilenetv3"][
                            "validation_error"
                        ]
                        * 4,
                    ),
                )
        run.status, run.stage, run.progress = "COMPLETED", "COMPLETED", 100
        run.sample_count = len(train) + len(validation)
        run.training_count, run.validation_count = len(train), len(validation)
        run.dataset_hash, run.metrics_json, run.model_id = (
            snapshot["sha256"],
            metrics,
            records[0].id,
        )
        run.completed_at = datetime.now(UTC)
        db.add(
            AuditLog(
                user_id=None,
                action="TRAINING_COMPLETED",
                target_type="training_run",
                target_id=str(run_id),
                details_json={
                    "dataset_hash": snapshot["sha256"],
                    "artifact_ids": metrics["artifact_ids"],
                    "fine_tuned_reader": bool(fine_metrics),
                    "holdout_samples": len(holdout),
                    "auto_activation": False,
                },
                ip_address=None,
            )
        )
        db.commit()
