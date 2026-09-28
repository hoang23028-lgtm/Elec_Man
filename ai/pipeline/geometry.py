import cv2
import numpy as np

NormalizedPoint = tuple[float, float]


def normalized_bbox_polygon(
    bbox: tuple[float, float, float, float],
) -> tuple[NormalizedPoint, NormalizedPoint, NormalizedPoint, NormalizedPoint]:
    x, y, width, height = bbox
    return ((x, y), (x + width, y), (x + width, y + height), (x, y + height))


def perspective_crop(
    image: np.ndarray,
    polygon: tuple[NormalizedPoint, NormalizedPoint, NormalizedPoint, NormalizedPoint],
) -> np.ndarray:
    """Rectify an ordered TL, TR, BR, BL quadrilateral into a flat crop."""
    height, width = image.shape[:2]
    source = np.float32(
        [
            [min(1.0, max(0.0, x)) * width, min(1.0, max(0.0, y)) * height]
            for x, y in polygon
        ]
    )
    top = np.linalg.norm(source[1] - source[0])
    bottom = np.linalg.norm(source[2] - source[3])
    left = np.linalg.norm(source[3] - source[0])
    right = np.linalg.norm(source[2] - source[1])
    output_width = max(2, int(round(max(top, bottom))))
    output_height = max(2, int(round(max(left, right))))
    target = np.float32(
        [
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1],
        ]
    )
    transform = cv2.getPerspectiveTransform(source, target)
    return cv2.warpPerspective(
        image,
        transform,
        (output_width, output_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
