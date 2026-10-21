"""Register supervision robust to the upstream meter's localization errors."""

import numpy as np

from ai.pipeline.geometry import (
    normalized_bbox_polygon,
    perspective_crop,
    transform_polygon,
)
from ai.pipeline.localization import MeterLocator
from ai.training.keypoint_regressor import valid_polygon


def register_samples(
    image, reading_polygon, meter_model, *, training_frame=None, rng=None
):
    """Validation gets only the predicted frame, never the annotated meter.

    Training adds the true frame and two bounded geometric perturbations. The
    reading corners are transformed alongside each crop; labels are not edited.
    """
    height, width = image.shape[:2]
    located = MeterLocator(meter_model).locate(image)
    predicted_frame = located.meter_polygon or normalized_bbox_polygon(
        tuple(
            v / s
            for v, s in zip(
                located.meter_region, (width, height, width, height), strict=True
            )
        )
    )
    frames = [predicted_frame]
    if training_frame is not None:
        frames.append(training_frame)
        rng = rng if rng is not None else np.random.default_rng(42)
        for scale in (0.015, 0.035):
            jittered = np.clip(
                np.asarray(training_frame) + rng.uniform(-scale, scale, (4, 2)), 0, 1
            ).astype(np.float32)
            if valid_polygon(jittered):
                frames.append(tuple(tuple(p) for p in jittered))
    for frame in frames:
        yield perspective_crop(image, frame), transform_polygon(reading_polygon, frame)
