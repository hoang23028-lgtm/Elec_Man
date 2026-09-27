"use client";

import { KeyboardEvent, PointerEvent, useRef, useState } from "react";

import type { ReadingBoundingBox } from "@/services/results";

type Props = {
  imageUrl: string;
  imageAlt: string;
  value: ReadingBoundingBox | null;
  onChange: (value: ReadingBoundingBox | null) => void;
};

type Point = { x: number; y: number };
type Corner = "north-west" | "north-east" | "south-east" | "south-west";
type ResizeSession = { corner: Corner; initial: ReadingBoundingBox };

const minimumSize = 0.005;
const keyboardStep = 0.005;

function clamp(value: number, minimum = 0, maximum = 1) {
  return Math.min(maximum, Math.max(minimum, value));
}

function rounded(value: number) {
  return Math.round(value * 10000) / 10000;
}

function boxFromPoints(start: Point, end: Point): ReadingBoundingBox {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  return {
    x: rounded(x),
    y: rounded(y),
    width: rounded(Math.min(1 - x, Math.max(minimumSize, Math.abs(end.x - start.x)))),
    height: rounded(Math.min(1 - y, Math.max(minimumSize, Math.abs(end.y - start.y)))),
  };
}

function resizeFromCorner(
  initial: ReadingBoundingBox,
  corner: Corner,
  pointer: Point,
): ReadingBoundingBox {
  const left = initial.x;
  const top = initial.y;
  const right = initial.x + initial.width;
  const bottom = initial.y + initial.height;

  if (corner === "north-west") {
    const x = clamp(pointer.x, 0, right - minimumSize);
    const y = clamp(pointer.y, 0, bottom - minimumSize);
    return { x: rounded(x), y: rounded(y), width: rounded(right - x), height: rounded(bottom - y) };
  }
  if (corner === "north-east") {
    const nextRight = clamp(pointer.x, left + minimumSize, 1);
    const y = clamp(pointer.y, 0, bottom - minimumSize);
    return { x: rounded(left), y: rounded(y), width: rounded(nextRight - left), height: rounded(bottom - y) };
  }
  if (corner === "south-east") {
    const nextRight = clamp(pointer.x, left + minimumSize, 1);
    const nextBottom = clamp(pointer.y, top + minimumSize, 1);
    return { x: rounded(left), y: rounded(top), width: rounded(nextRight - left), height: rounded(nextBottom - top) };
  }
  const x = clamp(pointer.x, 0, right - minimumSize);
  const nextBottom = clamp(pointer.y, top + minimumSize, 1);
  return { x: rounded(x), y: rounded(top), width: rounded(right - x), height: rounded(nextBottom - top) };
}

function cornerPoint(box: ReadingBoundingBox, corner: Corner): Point {
  return {
    x: corner.endsWith("east") ? box.x + box.width : box.x,
    y: corner.startsWith("south") ? box.y + box.height : box.y,
  };
}

export function ReadingRegionAnnotator({ imageUrl, imageAlt, value, onChange }: Props) {
  const surfaceRef = useRef<HTMLDivElement>(null);
  const startRef = useRef<Point | null>(null);
  const resizeRef = useRef<ResizeSession | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [resizingCorner, setResizingCorner] = useState<Corner | null>(null);

  function pointerPosition(clientX: number, clientY: number): Point {
    const bounds = surfaceRef.current?.getBoundingClientRect();
    if (!bounds) return { x: 0, y: 0 };
    return {
      x: clamp((clientX - bounds.left) / bounds.width),
      y: clamp((clientY - bounds.top) / bounds.height),
    };
  }

  function beginDrawing(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0 || event.target !== event.currentTarget) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const pointer = pointerPosition(event.clientX, event.clientY);
    const start = {
      x: Math.min(1 - minimumSize, pointer.x),
      y: Math.min(1 - minimumSize, pointer.y),
    };
    startRef.current = start;
    setDrawing(true);
    onChange({ x: start.x, y: start.y, width: minimumSize, height: minimumSize });
  }

  function continueDrawing(event: PointerEvent<HTMLDivElement>) {
    if (!drawing || !startRef.current) return;
    onChange(boxFromPoints(startRef.current, pointerPosition(event.clientX, event.clientY)));
  }

  function endDrawing(event: PointerEvent<HTMLDivElement>) {
    if (!drawing || !startRef.current) return;
    onChange(boxFromPoints(startRef.current, pointerPosition(event.clientX, event.clientY)));
    startRef.current = null;
    setDrawing(false);
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  function beginResizing(event: PointerEvent<HTMLButtonElement>, corner: Corner) {
    if (event.button !== 0 || !value) return;
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeRef.current = { corner, initial: value };
    setResizingCorner(corner);
  }

  function continueResizing(event: PointerEvent<HTMLButtonElement>) {
    const session = resizeRef.current;
    if (!session) return;
    onChange(
      resizeFromCorner(
        session.initial,
        session.corner,
        pointerPosition(event.clientX, event.clientY),
      ),
    );
  }

  function endResizing(event: PointerEvent<HTMLButtonElement>) {
    if (!resizeRef.current) return;
    continueResizing(event);
    resizeRef.current = null;
    setResizingCorner(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function cancelResizing(event: PointerEvent<HTMLButtonElement>) {
    const session = resizeRef.current;
    if (!session) return;
    onChange(session.initial);
    resizeRef.current = null;
    setResizingCorner(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function adjustCornerWithKeyboard(event: KeyboardEvent<HTMLButtonElement>, corner: Corner) {
    if (!value || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const step = event.shiftKey ? keyboardStep * 4 : keyboardStep;
    const point = cornerPoint(value, corner);
    if (event.key === "ArrowLeft") point.x -= step;
    if (event.key === "ArrowRight") point.x += step;
    if (event.key === "ArrowUp") point.y -= step;
    if (event.key === "ArrowDown") point.y += step;
    onChange(resizeFromCorner(value, corner, point));
  }

  function updatePercentage(field: keyof ReadingBoundingBox, rawValue: string) {
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;
    const current = value ?? { x: 0, y: 0, width: 0.1, height: 0.1 };
    const isSize = field === "width" || field === "height";
    const normalized = clamp(parsed / 100, isSize ? minimumSize : 0, isSize ? 1 : 1 - minimumSize);
    const next = { ...current, [field]: rounded(normalized) };
    if (field === "x") next.width = Math.min(next.width, 1 - next.x);
    if (field === "y") next.height = Math.min(next.height, 1 - next.y);
    if (field === "width") next.width = Math.max(minimumSize, Math.min(next.width, 1 - next.x));
    if (field === "height") next.height = Math.max(minimumSize, Math.min(next.height, 1 - next.y));
    onChange(next);
  }

  const fields: Array<{ key: keyof ReadingBoundingBox; label: string }> = [
    { key: "x", label: "Trái (%)" },
    { key: "y", label: "Trên (%)" },
    { key: "width", label: "Rộng (%)" },
    { key: "height", label: "Cao (%)" },
  ];

  return (
    <div className="reading-annotator">
      <div
        ref={surfaceRef}
        className={`reading-annotator-surface${drawing ? " drawing" : ""}${resizingCorner ? " resizing" : ""}`}
        onPointerDown={beginDrawing}
        onPointerMove={continueDrawing}
        onPointerUp={endDrawing}
        onPointerCancel={endDrawing}
        aria-label="Kéo để khoanh vùng chứa các chữ số điện"
      >
        {/* The authenticated image is loaded directly in the browser. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={imageUrl} alt={imageAlt} draggable={false} />
        {value && (
          <div
            className="reading-selection"
            style={{
              left: `${value.x * 100}%`,
              top: `${value.y * 100}%`,
              width: `${value.width * 100}%`,
              height: `${value.height * 100}%`,
            }}
          >
            <span>Vùng chỉ số</span>
            {(
              [
                ["north-west", "Góc trên trái"],
                ["north-east", "Góc trên phải"],
                ["south-east", "Góc dưới phải"],
                ["south-west", "Góc dưới trái"],
              ] as Array<[Corner, string]>
            ).map(([corner, label]) => (
              <button
                key={corner}
                type="button"
                className={`reading-resize-handle ${corner}`}
                aria-label={`${label}. Kéo hoặc dùng các phím mũi tên để điều chỉnh`}
                onPointerDown={(event) => beginResizing(event, corner)}
                onPointerMove={continueResizing}
                onPointerUp={endResizing}
                onPointerCancel={cancelResizing}
                onKeyDown={(event) => adjustCornerWithKeyboard(event, corner)}
              />
            ))}
          </div>
        )}
      </div>
      <aside className="reading-annotator-controls" aria-label="Tọa độ vùng chỉ số">
        <div>
          <p className="eyebrow">Nhãn huấn luyện</p>
          <h4>Khoanh vùng dãy số điện</h4>
          <p className="muted">
            Kéo từ góc trên trái đến góc dưới phải của các số màu đen. Không lấy bánh số đỏ
            sau dấu phẩy. Sau khi tạo khung, kéo một trong bốn góc để tinh chỉnh. Có thể chọn
            từng góc và dùng phím mũi tên; giữ Shift để điều chỉnh nhanh hơn.
          </p>
        </div>
        <div className="reading-coordinate-grid">
          {fields.map((field) => (
            <label key={field.key}>
              {field.label}
              <input
                type="number"
                min={field.key === "width" || field.key === "height" ? 0.5 : 0}
                max={100}
                step={0.1}
                value={value ? Math.round(value[field.key] * 1000) / 10 : ""}
                placeholder="0"
                onChange={(event) => updatePercentage(field.key, event.target.value)}
              />
            </label>
          ))}
        </div>
        <button type="button" className="secondary" onClick={() => onChange(null)} disabled={!value}>
          Xóa vùng đã chọn
        </button>
        <p className={`annotation-status ${value ? "complete" : ""}`} role="status">
          {value
            ? "Đã có vùng chỉ số. Đóng cửa sổ và bấm Lưu thay đổi hoặc Xác nhận."
            : "Chưa có vùng chỉ số — ảnh này sẽ chưa được dùng để huấn luyện."}
        </p>
      </aside>
    </div>
  );
}
