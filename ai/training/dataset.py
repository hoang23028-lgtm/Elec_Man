import json
import shutil
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import cv2

from ai.pipeline.geometry import perspective_crop
from ai.pipeline.preprocessing import load_prepared_image
from ai.pipeline.register import integer_register_strip


def _reading_polygon(reading) -> tuple[tuple[float, float], ...]:
    points = (reading.reading_polygon_json or {}).get("points")
    if not isinstance(points, list) or len(points) != 4:
        raise ValueError("Nhãn vùng chỉ số không hợp lệ.")
    return tuple((float(point["x"]), float(point["y"])) for point in points)


def export_sequence_dataset(
    training_rows,
    validation_rows,
    storage_root: Path,
    target: Path,
    holdout_rows=None,
) -> dict:
    """Create deterministic whole-register crops without exposing source photos."""
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    if target.exists():
        raise ValueError("Bộ dữ liệu chuỗi của phiên huấn luyện đã tồn tại.")
    temporary.mkdir(parents=True)
    manifest: list[dict] = []
    try:
        splits = [("train", training_rows), ("validation", validation_rows)]
        if holdout_rows is not None:
            splits.append(("holdout", holdout_rows))
        for split, rows in splits:
            image_dir = temporary / split
            image_dir.mkdir()
            labels: list[str] = []
            for image, reading in rows:
                label = str(reading.final_meter_reading or "").strip()
                if (
                    not label.isascii()
                    or not label.isdigit()
                    or not 4 <= len(label) <= 8
                ):
                    raise ValueError("Nhãn chỉ số phải gồm 4–8 chữ số nguyên.")
                source = load_prepared_image(storage_root / image.relative_path)
                if source is None:
                    raise ValueError("Không thể giải mã ảnh đã gắn nhãn.")
                crop = integer_register_strip(
                    perspective_crop(source, _reading_polygon(reading))
                )
                relative_path = f"{split}/{image.sha256}.png"
                output = temporary / relative_path
                if not cv2.imwrite(str(output), crop):
                    raise OSError("Không thể ghi ảnh crop cho bộ dữ liệu chuỗi.")
                labels.append(f"{relative_path}\t{label}")
                manifest.append(
                    {
                        "split": split,
                        "source_sha256": image.sha256,
                        "crop_sha256": sha256(output.read_bytes()).hexdigest(),
                        "label": label,
                    }
                )
            (temporary / f"{split}.tsv").write_text(
                "\n".join(labels) + ("\n" if labels else ""), encoding="utf-8"
            )
        manifest.sort(key=lambda row: (row["split"], row["source_sha256"]))
        manifest_bytes = json.dumps(
            manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        (temporary / "manifest.json").write_bytes(manifest_bytes)
        temporary.replace(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {
        "path": target.name,
        "train_samples": len(training_rows),
        "validation_samples": len(validation_rows),
        "holdout_samples": len(holdout_rows or []),
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "format": "image-tab-label-tsv-v1",
    }
