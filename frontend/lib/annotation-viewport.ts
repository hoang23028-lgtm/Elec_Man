import type { ReadingBoundingBox, ReadingPolygon } from "../services/results";

export function polygonBounds(polygon: ReadingPolygon | null): ReadingBoundingBox | null {
  if (!polygon || polygon.points.length !== 4) return null;
  const xs = polygon.points.map((p) => p.x), ys = polygon.points.map((p) => p.y);
  return { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - Math.min(...ys) };
}

export function regionViewport(box: ReadingBoundingBox, fitWidth: number, aspect: number, width: number, height: number) {
  if (![box.x, box.y, box.width, box.height, fitWidth, aspect, width, height].every(Number.isFinite)
    || box.x < 0 || box.y < 0 || box.width <= 0 || box.height <= 0
    || box.x + box.width > 1.001 || box.y + box.height > 1.001
    || fitWidth <= 0 || aspect <= 0 || width <= 0 || height <= 0) return null;
  const zoom = Math.max(1, Math.min(12, width * .85 / (fitWidth * box.width), height * .85 / (fitWidth / aspect * box.height)));
  const imageWidth = fitWidth * zoom, imageHeight = imageWidth / aspect;
  return {
    zoom,
    left: Math.max(0, Math.min(imageWidth - width, (box.x + box.width / 2) * imageWidth - width / 2)),
    top: Math.max(0, Math.min(imageHeight - height, (box.y + box.height / 2) * imageHeight - height / 2)),
  };
}
