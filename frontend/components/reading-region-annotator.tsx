"use client";

import {
  KeyboardEvent,
  PointerEvent,
  WheelEvent as ReactWheelEvent,
  useRef,
  useState,
} from "react";

import type { ReadingBoundingBox, ReadingPoint, ReadingPolygon } from "@/services/results";

type Props = {
  imageUrl: string; imageAlt: string; value: ReadingPolygon | null;
  automaticValue: ReadingBoundingBox | null;
  onChange: (value: ReadingPolygon | null) => void;
  onRecognize: () => void; recognizing: boolean;
  recognitionStatus: string | null; canRecognize: boolean;
};
type DragSession = { index: number; initial: ReadingPolygon };
const keyboardStep = 0.005;
const minimumArea = 0.000025;
const minimumZoom = 1;
const maximumZoom = 4;
const zoomStep = 0.25;
const cornerLabels = ["Góc trên trái", "Góc trên phải", "Góc dưới phải", "Góc dưới trái"];

function clamp(value: number) { return Math.min(1, Math.max(0, value)); }
function rounded(value: number) { return Math.round(clamp(value) * 10000) / 10000; }
function signedArea(points: ReadingPoint[]) {
  return points.reduce((area, point, index) => {
    const next = points[(index + 1) % points.length];
    return area + point.x * next.y - point.y * next.x;
  }, 0) / 2;
}
function orientation(a: ReadingPoint, b: ReadingPoint, c: ReadingPoint) {
  return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}
function segmentsCross(a: ReadingPoint, b: ReadingPoint, c: ReadingPoint, d: ReadingPoint) {
  return orientation(a, b, c) * orientation(a, b, d) < 0
    && orientation(c, d, a) * orientation(c, d, b) < 0;
}
function validPolygon(points: ReadingPoint[]) {
  if (points.length !== 4) return false;
  const turns = points.map((point, index) => orientation(
    point, points[(index + 1) % 4], points[(index + 2) % 4],
  ));
  return Math.abs(signedArea(points)) >= minimumArea
    && !segmentsCross(points[0], points[1], points[2], points[3])
    && !segmentsCross(points[1], points[2], points[3], points[0])
    && (turns.every((turn) => turn > 0) || turns.every((turn) => turn < 0));
}
function orderPoints(points: ReadingPoint[]): ReadingPoint[] {
  const center = {
    x: points.reduce((sum, point) => sum + point.x, 0) / points.length,
    y: points.reduce((sum, point) => sum + point.y, 0) / points.length,
  };
  const sorted = [...points].sort((left, right) =>
    Math.atan2(left.y - center.y, left.x - center.x)
    - Math.atan2(right.y - center.y, right.x - center.x));
  const firstIndex = sorted.reduce((best, point, index) =>
    point.x + point.y < sorted[best].x + sorted[best].y ? index : best, 0);
  let ordered = [...sorted.slice(firstIndex), ...sorted.slice(0, firstIndex)];
  if (signedArea(ordered) < 0) ordered = [ordered[0], ordered[3], ordered[2], ordered[1]];
  return ordered.map((point) => ({ x: rounded(point.x), y: rounded(point.y) }));
}
function svgPoints(points: ReadingPoint[]) {
  return points.map((point) => `${point.x * 100},${point.y * 100}`).join(" ");
}

export function ReadingRegionAnnotator({ imageUrl, imageAlt, value, automaticValue,
  onChange, onRecognize, recognizing, recognitionStatus, canRecognize }: Props) {
  const surfaceRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragSession | null>(null);
  const [draftPoints, setDraftPoints] = useState<ReadingPoint[]>([]);
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);

  function pointerPosition(clientX: number, clientY: number): ReadingPoint {
    const bounds = surfaceRef.current?.getBoundingClientRect();
    if (!bounds) return { x: 0, y: 0 };
    return { x: rounded((clientX - bounds.left) / bounds.width), y: rounded((clientY - bounds.top) / bounds.height) };
  }
  function addPoint(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0 || value || recognizing) return;
    const next = [...draftPoints, pointerPosition(event.clientX, event.clientY)];
    if (next.length < 4) { setDraftPoints(next); return; }
    const ordered = orderPoints(next);
    if (validPolygon(ordered)) onChange({ points: ordered });
    setDraftPoints([]);
  }
  function beginDragging(event: PointerEvent<HTMLButtonElement>, index: number) {
    if (event.button !== 0 || !value || recognizing) return;
    event.stopPropagation(); event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { index, initial: value }; setDraggingIndex(index);
  }
  function continueDragging(event: PointerEvent<HTMLButtonElement>) {
    const session = dragRef.current;
    if (!session || !value) return;
    const points = value.points.map((point, index) => index === session.index ? pointerPosition(event.clientX, event.clientY) : point);
    if (validPolygon(points)) onChange({ points });
  }
  function endDragging(event: PointerEvent<HTMLButtonElement>) {
    if (!dragRef.current) return;
    continueDragging(event); dragRef.current = null; setDraggingIndex(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  function cancelDragging(event: PointerEvent<HTMLButtonElement>) {
    if (dragRef.current) onChange(dragRef.current.initial);
    dragRef.current = null; setDraggingIndex(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  function adjustPointWithKeyboard(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!value || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
    event.preventDefault();
    const step = event.shiftKey ? keyboardStep * 4 : keyboardStep;
    const points = value.points.map((point) => ({ ...point }));
    if (event.key === "ArrowLeft") points[index].x = rounded(points[index].x - step);
    if (event.key === "ArrowRight") points[index].x = rounded(points[index].x + step);
    if (event.key === "ArrowUp") points[index].y = rounded(points[index].y - step);
    if (event.key === "ArrowDown") points[index].y = rounded(points[index].y + step);
    if (validPolygon(points)) onChange({ points });
  }
  function updateCoordinate(index: number, axis: "x" | "y", rawValue: string) {
    if (!value) return;
    const parsed = Number(rawValue); if (!Number.isFinite(parsed)) return;
    const points = value.points.map((point) => ({ ...point }));
    points[index][axis] = rounded(parsed / 100);
    if (validPolygon(points)) onChange({ points });
  }
  function resetSelection() { setDraftPoints([]); onChange(null); }
  function applyZoom(requestedZoom: number) {
    const nextZoom = Math.min(maximumZoom, Math.max(minimumZoom, requestedZoom));
    if (nextZoom === zoom) return;
    const viewport = viewportRef.current;
    const horizontalCenter = viewport ? viewport.scrollLeft + viewport.clientWidth / 2 : 0;
    const verticalCenter = viewport ? viewport.scrollTop + viewport.clientHeight / 2 : 0;
    const ratio = nextZoom / zoom;
    setZoom(nextZoom);
    if (viewport) {
      window.requestAnimationFrame(() => {
        viewport.scrollLeft = horizontalCenter * ratio - viewport.clientWidth / 2;
        viewport.scrollTop = verticalCenter * ratio - viewport.clientHeight / 2;
      });
    }
  }
  function zoomWithWheel(event: ReactWheelEvent<HTMLDivElement>) {
    if (!event.ctrlKey) return;
    event.preventDefault();
    applyZoom(zoom + (event.deltaY < 0 ? zoomStep : -zoomStep));
  }
  const drawingPoints = value?.points ?? draftPoints;

  return <div className="reading-annotator">
    <div className="reading-annotator-workspace">
      <div className="reading-zoom-toolbar" aria-label="Điều khiển thu phóng ảnh">
        <button type="button" onClick={() => applyZoom(zoom - zoomStep)} disabled={zoom <= minimumZoom} aria-label="Thu nhỏ ảnh">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14" /></svg>
        </button>
        <output aria-live="polite" aria-label={`Mức thu phóng ${Math.round(zoom * 100)} phần trăm`}>{Math.round(zoom * 100)}%</output>
        <button type="button" onClick={() => applyZoom(zoom + zoomStep)} disabled={zoom >= maximumZoom} aria-label="Phóng to ảnh">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        </button>
        <button type="button" className="reading-zoom-reset" onClick={() => applyZoom(1)} disabled={zoom === 1}>Đặt lại</button>
        <span>Giữ Ctrl và cuộn chuột để zoom</span>
      </div>
      <div ref={viewportRef} className="reading-annotator-viewport" onWheel={zoomWithWheel}>
        <div ref={surfaceRef} style={{ width: `${zoom * 100}%` }} className={`reading-annotator-surface polygon-mode${draggingIndex !== null ? " resizing" : ""}`}
          onPointerDown={addPoint} aria-label="Bấm lần lượt bốn góc của vùng chứa các chữ số điện">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageUrl} alt={imageAlt} draggable={false} />
          {automaticValue && <div className="automatic-reading-selection" style={{ left: `${automaticValue.x * 100}%`, top: `${automaticValue.y * 100}%`, width: `${automaticValue.width * 100}%`, height: `${automaticValue.height * 100}%` }}><span>Vùng tự động</span></div>}
          {drawingPoints.length > 0 && <svg className="reading-polygon-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {value ? <polygon className="reading-polygon complete" points={svgPoints(drawingPoints)} /> : <polyline className="reading-polygon draft" points={svgPoints(drawingPoints)} />}
          </svg>}
          {drawingPoints.map((point, index) => value ? <button key={index} type="button" className="reading-point-handle"
            style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
            aria-label={`${cornerLabels[index]}. Kéo hoặc dùng phím mũi tên để điều chỉnh`}
            onPointerDown={(event) => beginDragging(event, index)} onPointerMove={continueDragging}
            onPointerUp={endDragging} onPointerCancel={cancelDragging}
            onKeyDown={(event) => adjustPointWithKeyboard(event, index)}><span aria-hidden="true" /></button>
            : <span key={index} className="reading-draft-point" style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }} aria-hidden="true" />)}
          {value && <span className="reading-polygon-label">Vùng người dùng</span>}
        </div>
      </div>
    </div>
    <aside className="reading-annotator-controls" aria-label="Tọa độ vùng chỉ số">
      <div><p className="eyebrow">Nhãn huấn luyện</p><h4>Nối bốn góc của dãy số điện</h4>
        <p className="muted">Bấm lần lượt vào 4 góc quanh các số màu đen; hệ thống tự nối thành vùng. Sau đó kéo từng điểm để xoay chéo hoặc hiệu chỉnh phối cảnh. Không lấy bánh số đỏ sau dấu phẩy. Có thể dùng phím mũi tên; giữ Shift để di chuyển nhanh hơn.</p></div>
      {value ? <div className="reading-polygon-coordinates">{value.points.map((point, index) => <fieldset key={index}>
        <legend>{cornerLabels[index]}</legend>
        <label>X (%)<input type="number" min={0} max={100} step={0.1} value={Math.round(point.x * 1000) / 10} onChange={(event) => updateCoordinate(index, "x", event.target.value)} /></label>
        <label>Y (%)<input type="number" min={0} max={100} step={0.1} value={Math.round(point.y * 1000) / 10} onChange={(event) => updateCoordinate(index, "y", event.target.value)} /></label>
      </fieldset>)}</div> : <p className="annotation-progress" role="status">Đã chọn {draftPoints.length}/4 điểm</p>}
      <div className="reading-annotator-actions">
        <button type="button" onClick={onRecognize} disabled={!value || recognizing || !canRecognize}>{recognizing ? "Đang xác định chỉ số…" : "Xác định chỉ số"}</button>
        <button type="button" className="secondary" onClick={resetSelection} disabled={(!value && !draftPoints.length) || recognizing}>{value ? "Vẽ lại vùng" : "Xóa các điểm"}</button>
      </div>
      <p className={`annotation-status ${value ? "complete" : ""}`} role="status">
        {recognitionStatus ?? (!canRecognize ? "Chỉ có thể xác định lại chỉ số khi kết quả đang ở danh sách Cần xử lý." : value ? "Đã nối đủ bốn điểm. Bấm Xác định chỉ số để OCR vùng màu đỏ sau hiệu chỉnh phối cảnh." : `Hãy bấm thêm ${4 - draftPoints.length} điểm để hoàn thành vùng chỉ số.`)}
      </p>
    </aside>
  </div>;
}
