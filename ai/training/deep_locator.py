"""Frozen ImageNet MobileNetV3 features + supervised four-corner head.

One meter per image, not a multi-object YOLO detector. Runtime artifact is ONNX;
Torch and upstream weights are confined to the trainer image.
"""

from pathlib import Path
from time import monotonic, perf_counter

import cv2
import numpy as np

from ai.pipeline.geometry import normalized_bbox_polygon
from ai.training.keypoint_regressor import order_polygon, valid_polygon
from ai.training.metrics import polygon_iou

ARCHITECTURE = "mobilenet-v3-small-spatial-keypoints-v2"
INPUT_SIZE = 320
SPATIAL_GRID = 5
# Read-only artifact compatibility, not a second training implementation.
READABLE_INPUT_SIZES = {
    "mobilenet-v3-small-spatial-keypoints-v1": 192,
    ARCHITECTURE: INPUT_SIZE,
}


def image_tensor(image, size=INPUT_SIZE):
    rgb = cv2.cvtColor(cv2.resize(image, (size, size)), cv2.COLOR_BGR2RGB)
    values = rgb.transpose(2, 0, 1).astype(np.float32) / 255
    return (
        values - np.array([0.485, 0.456, 0.406], np.float32)[:, None, None]
    ) / np.array([0.229, 0.224, 0.225], np.float32)[:, None, None]


class DeepRegionLocator:
    def __init__(self, path: Path):
        import onnxruntime as ort

        ort.disable_telemetry_events()

        if path.suffix != ".onnx" or path.stat().st_size > 40 * 1024**2:
            raise ValueError("Artifact định vị học sâu không hợp lệ.")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        metadata = self.session.get_modelmeta().custom_metadata_map
        self.architecture = metadata.get("architecture")
        if self.architecture not in READABLE_INPUT_SIZES:
            raise ValueError("Kiến trúc định vị không tương thích.")
        self.size = READABLE_INPUT_SIZES[self.architecture]
        self.coordinate_space = metadata.get("coordinate_space")
        self.validation_error = float(metadata.get("validation_error", "nan"))
        inputs, outputs = self.session.get_inputs(), self.session.get_outputs()
        if (
            self.coordinate_space not in {"image", "meter"}
            or not np.isfinite(self.validation_error)
            or not 0 <= self.validation_error <= 1
            or len(inputs) != 1
            or inputs[0].name != "image"
            or inputs[0].shape != [1, 3, self.size, self.size]
            or inputs[0].type != "tensor(float)"
            or len(outputs) != 1
            or outputs[0].shape != [1, 8]
        ):
            raise ValueError("Contract artifact định vị không hợp lệ.")

    @classmethod
    def load(cls, path):
        return cls(path)

    def predict(self, image):
        values = self.session.run(
            None, {"image": image_tensor(image, self.size)[None]}
        )[0]
        if values.shape != (1, 8) or not np.isfinite(values).all():
            return None
        if np.any(values < 0) or np.any(values > 1):
            return None
        points = order_polygon(values.reshape(4, 2))
        if not valid_polygon(points):
            return None
        # Validation error is a heuristic, never a calibrated probability.
        confidence = min(0.899, max(0.0, 1 - self.validation_error * 4))
        return tuple((float(x), float(y)) for x, y in points), confidence

    predict_region = predict


def load_region_model(path):
    from ai.training.keypoint_regressor import KeypointRegionRegressor

    return (
        DeepRegionLocator.load(path)
        if path.suffix == ".onnx"
        else KeypointRegionRegressor.load(path)
    )


def train_deep_locator(
    train,
    validation,
    artifact,
    *,
    coordinate_space,
    epochs=40,
    checkpoint=None,
    max_seconds=900,
):
    """Iterable (image, polygon) rows; select head by validation, never holdout."""
    import onnx
    import torch
    from torch import nn
    from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

    if artifact.exists():
        raise ValueError("Không được ghi đè artifact định vị.")
    if coordinate_space not in {"image", "meter"} or not 1 <= epochs <= 100:
        raise ValueError("Cấu hình bộ định vị không hợp lệ.")
    deadline = monotonic() + max_seconds
    torch.set_num_threads(1)
    torch.manual_seed(42)
    backbone = nn.Sequential(
        mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1).features,
        nn.AdaptiveAvgPool2d((SPATIAL_GRID, SPATIAL_GRID)),
        nn.Flatten(),
    ).eval()
    backbone.requires_grad_(False)

    def features(rows):
        encoded, targets = [], []
        for image, polygon in rows:
            if checkpoint:
                checkpoint()
            if monotonic() > deadline:
                raise TimeoutError("Định vị học sâu vượt ngân sách thời gian.")
            with torch.inference_mode():
                feature = backbone(torch.from_numpy(image_tensor(image)[None]))
            encoded.append(feature.clone())
            targets.append(np.asarray(polygon, np.float32).reshape(8))
        if not encoded:
            raise ValueError("Thiếu mẫu định vị.")
        return torch.cat(encoded), torch.from_numpy(np.stack(targets))

    x, y = features(train)
    vx, vy = features(validation)
    if len(x) < 2:
        raise ValueError("Cần ít nhất hai mẫu học định vị.")
    head = nn.Sequential(
        nn.Linear(x.shape[1], 128), nn.ReLU(), nn.Linear(128, 8), nn.Sigmoid()
    )
    with torch.no_grad():
        head[2].weight.zero_()
        head[2].bias.copy_(torch.logit(y.mean(0).clamp(0.001, 0.999)))
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.001, weight_decay=0.01)
    best, history, iou_history = None, [], []
    # Thin registers need small vertical errors; normalize each axis by target
    # extent rather than giving a whole meter and a thin strip the same loss.
    polygons = y.reshape(-1, 4, 2)
    extent = (polygons.amax(1) - polygons.amin(1)).clamp(min=0.05)
    weights = extent.reciprocal().repeat(1, 4)
    for epoch in range(epochs):
        if checkpoint:
            checkpoint()
        if monotonic() > deadline:
            raise TimeoutError("Định vị học sâu vượt ngân sách thời gian.")
        head.train()
        order = torch.randperm(len(x))
        for start in range(0, len(x), 32):
            batch = order[start : start + 32]
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.smooth_l1_loss(
                head(x[batch]) * weights[batch], y[batch] * weights[batch]
            )
            if not torch.isfinite(loss):
                raise ValueError("Loss định vị không hữu hạn.")
            loss.backward()
            nn.utils.clip_grad_norm_(head.parameters(), 1)
            optimizer.step()
        head.eval()
        with torch.inference_mode():
            predicted = head(vx)
            error = float((predicted - vy).abs().mean())
            mean_iou = float(
                np.mean(
                    [
                        polygon_iou(order_polygon(p.reshape(4, 2)), t.reshape(4, 2))
                        for p, t in zip(predicted.numpy(), vy.numpy(), strict=True)
                    ]
                )
            )
        history.append(error)
        iou_history.append(mean_iou)
        # Validation selects weights; holdout is never used for this choice.
        rank = (mean_iou, -error)
        if best is None or rank > best[3]:
            best = (
                error,
                epoch + 1,
                {k: v.detach().clone() for k, v in head.state_dict().items()},
                rank,
            )
    head.load_state_dict(best[2])
    model = nn.Sequential(backbone, head).eval()
    artifact.parent.mkdir(parents=True, exist_ok=True)
    temporary = artifact.with_suffix(".tmp.onnx")
    torch.onnx.export(
        model,
        torch.zeros(1, 3, INPUT_SIZE, INPUT_SIZE),
        str(temporary),
        opset_version=17,
        input_names=["image"],
        output_names=["corners"],
    )
    graph = onnx.load(str(temporary))
    onnx.helper.set_model_props(
        graph,
        {
            "architecture": ARCHITECTURE,
            "coordinate_space": coordinate_space,
            "validation_error": str(best[0]),
        },
    )
    onnx.checker.check_model(graph)
    onnx.save(graph, str(temporary))
    runtime = DeepRegionLocator(temporary)
    with torch.inference_mode():
        reference = model(torch.zeros(1, 3, INPUT_SIZE, INPUT_SIZE)).numpy()
    exported = runtime.session.run(
        None, {"image": np.zeros((1, 3, INPUT_SIZE, INPUT_SIZE), np.float32)}
    )[0]
    if not np.allclose(reference, exported, rtol=1e-4, atol=1e-5):
        raise ValueError("ONNX định vị không tương đương Torch.")
    temporary.replace(artifact)
    return DeepRegionLocator(artifact), {
        "architecture": ARCHITECTURE,
        "input_size": INPUT_SIZE,
        "spatial_grid": SPATIAL_GRID,
        "selection_metric": "validation_mean_iou",
        "encoder_frozen": True,
        "training_examples": len(x),
        "validation_examples": len(vx),
        "epochs": epochs,
        "best_epoch": best[1],
        "validation_error": best[0],
        "validation_history": history,
        "validation_iou_history": iou_history,
        "validation_mean_iou": iou_history[best[1] - 1],
        "onnx_parity": True,
        "score_calibrated": False,
    }


def benchmark_locators(
    rows, root, ridge_meter, ridge_region, deep_meter, deep_region, source, polygon
):
    """Same samples for both architectures; no label hints in full-chain locate."""
    from ai.pipeline.localization import MeterLocator, ReadingRegionLocator

    result = {}
    for name, meter_model, region_model in (
        ("ridge", ridge_meter, ridge_region),
        ("mobilenetv3", deep_meter, deep_region),
    ):
        meter_scores, reading_scores, times = [], [], []
        for image, reading in rows:
            prepared = source(root, image)
            started = perf_counter()
            meter = MeterLocator(meter_model).locate(prepared)
            region = ReadingRegionLocator(region_model).locate(prepared, meter)
            times.append((perf_counter() - started) * 1000)
            height, width = prepared.shape[:2]
            frame = meter.meter_polygon or normalized_bbox_polygon(
                tuple(
                    v / s
                    for v, s in zip(
                        meter.meter_region, (width, height, width, height), strict=True
                    )
                )
            )
            register = region.reading_polygon or normalized_bbox_polygon(
                tuple(
                    v / s
                    for v, s in zip(
                        region.reading_region,
                        (width, height, width, height),
                        strict=True,
                    )
                )
            )
            meter_scores.append(polygon_iou(frame, polygon(reading, "meter")))
            reading_scores.append(polygon_iou(register, polygon(reading)))
        result[name] = {
            "samples": len(rows),
            "meter_mean_iou": float(np.mean(meter_scores)) if rows else 0,
            "reading_mean_iou": float(np.mean(reading_scores)) if rows else 0,
            "p50_ms": float(np.percentile(times, 50)) if rows else None,
            "p95_ms": float(np.percentile(times, 95)) if rows else None,
        }
    return result
