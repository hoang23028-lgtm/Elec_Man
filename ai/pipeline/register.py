"""Small, dependency-light helpers for mechanical meter register images."""

import cv2
import numpy as np


def integer_register_strip(image: np.ndarray) -> np.ndarray:
    """Remove a red fractional wheel and labels below the mechanical register."""
    if image.size == 0 or image.ndim != 3 or image.shape[1] < 20:
        return image
    height, width = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red = (
        ((hsv[:, :, 0] <= 15) | (hsv[:, :, 0] >= 165))
        & (hsv[:, :, 1] >= 55)
        & (hsv[:, :, 2] >= 60)
    )
    column_counts = red.sum(axis=0)
    minimum_column_pixels = max(2, round(height * 0.12))
    columns = np.flatnonzero(
        (column_counts >= minimum_column_pixels)
        & (np.arange(width) >= round(width * 0.45))
    )
    if columns.size < max(2, round(width * 0.025)):
        return image
    groups = np.split(columns, np.where(np.diff(columns) > 1)[0] + 1)
    group = max(groups, key=lambda item: int(column_counts[item].sum()))
    if group.size < max(2, round(width * 0.025)):
        return image
    fractional_left = int(group[0])
    if fractional_left <= round(width * 0.5):
        return image
    wheel_pixels = np.argwhere(red[:, group])
    if wheel_pixels.size == 0:
        return image
    top = max(0, int(wheel_pixels[:, 0].min()) - round(height * 0.15))
    bottom = min(height, int(wheel_pixels[:, 0].max()) + 1 + round(height * 0.12))
    right = max(1, fractional_left - round(width * 0.01))
    cropped = image[top:bottom, :right]
    return cropped if cropped.size and cropped.shape[1] >= 20 else image
