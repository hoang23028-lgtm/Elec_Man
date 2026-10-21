"use client";

import { useCallback, useEffect, useState } from "react";
import { usePanelActive } from "@/components/section-tabs";
import { useLatestRequest } from "@/hooks/use-latest-request";
import { usePolling } from "@/hooks/use-polling";
import { trainingStatusLabel } from "@/lib/training-status";
import { getOperationalHealth, type OperationalHealth as Health } from "@/services/administration";

const stages: Record<string, string> = { decode: "Giải mã ảnh", preprocess: "Tiền xử lý", quality: "Chất lượng ảnh", meter_location: "Định vị công tơ", reading_region: "Định vị vùng số", scene_ocr: "OCR toàn ảnh", customer_ocr: "OCR mã khách hàng", crop: "Cắt vùng số", read_digits: "Đọc chuỗi số", validation: "Kiểm tra kết quả", crop_and_quality: "Cắt vùng / chất lượng", ppocr_rpc: "Dịch vụ PP-OCR", parseq_rpc: "Dịch vụ PARSeq" };

export function OperationalHealth() {
  const active = usePanelActive(); const request = useLatestRequest();
  const [data, setData] = useState<Health | null>(null); const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    const token = request.begin(); setLoading(true);
    try { const result = await getOperationalHealth(); if (request.isCurrent(token)) { setData(result); setError(null); } }
    catch (reason) { if (request.isCurrent(token)) setError(reason instanceof Error ? reason.message : "Không thể tải giám sát."); }
    finally { if (request.isCurrent(token)) setLoading(false); }
  }, [request]);
  useEffect(() => { if (active) void load(); return () => request.invalidate(); }, [active, load, request]);
  usePolling(load, 30000, active);
  return <section className="panel full-span" aria-labelledby="operational-health-title" aria-busy={loading}>
    <div className="section-heading"><div><p className="eyebrow">Giám sát</p><h2 id="operational-health-title">Hàng đợi, huấn luyện và sao lưu</h2><p className="muted">Tự làm mới mỗi 30 giây khi mở trang. Chỉ quản trị toàn hệ thống xem được.</p></div><button className="secondary" type="button" disabled={loading} onClick={() => void load()}>Làm mới</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="metrics"><div><strong>{data?.queue.PENDING ?? 0}</strong><span>Đang chờ</span></div><div><strong>{data?.queue.PROCESSING ?? 0}</strong><span>Đang xử lý</span></div><div><strong>{data?.stuck_jobs ?? 0}</strong><span>Quá thời hạn</span></div><div><strong>{data?.failed_last_24h ?? 0}</strong><span>Lỗi trong 24 giờ</span></div></div>
    {data?.alerts.map((alert) => <p className={alert.severity === "error" ? "error" : "notice"} key={alert.message}>{alert.message}</p>)}
    {data && <><p>Độ trễ p50: {data.latency.p50_ms == null ? "Chưa có" : `${Math.round(data.latency.p50_ms)} ms`} · p95: {data.latency.p95_ms == null ? "Chưa có" : `${Math.round(data.latency.p95_ms)} ms`} · {data.latency.samples} tác vụ gần nhất.</p><p className="muted">{data.note}</p>
      <p>Sao lưu: {data.backup?.verified ? `Đã kiểm tra checksum · ${data.backup.completed_at ? new Date(data.backup.completed_at).toLocaleString("vi-VN") : "Chưa rõ thời điểm"}` : "Chưa ghi nhận bản đã kiểm tra"}. Phải diễn tập phục hồi riêng và có bản sao ngoài máy chủ.</p>
      <p>Huấn luyện gần nhất: {data.training ? `${trainingStatusLabel(data.training.status)} · ${data.training.progress}%` : "Chưa có"}.</p>
      <details><summary>Thời gian từng bước OCR</summary><p className="muted">Tối đa 500 kết quả lưu gần nhất, tách nhận diện tự động và vùng khoanh thủ công. Hai dịch vụ đọc chạy song song; không cộng thời gian dịch vụ vào tổng lần nữa. Kết quả cũ thiếu đo từng bước không được suy đoán.</p>
        {["automatic", "manual"].map(group => { const rows = Object.entries(data.stage_latency?.[group] ?? {}); return <div key={group}><h3>{group === "automatic" ? "Nhận diện tự động" : "Vùng khoanh thủ công"}</h3>{rows.length ? <div className="table-wrap"><table><thead><tr><th>STT</th><th>Bước</th><th>Mẫu</th><th>p50</th><th>p95</th></tr></thead><tbody>{rows.map(([key, row], index) => <tr key={key}><td>{index + 1}</td><td>{stages[key] ?? key}</td><td>{row.samples}</td><td>{row.p50_ms.toFixed(1)} ms</td><td>{row.p95_ms.toFixed(1)} ms</td></tr>)}</tbody></table></div> : <p className="muted">Chưa có phép đo phù hợp. Xử lý ảnh mới để ghi thời gian.</p>}</div>; })}
      </details>
      <div className="table-wrap"><table><thead><tr><th>STT</th><th>Vùng lưu trữ</th><th>Còn trống</th></tr></thead><tbody>{Object.entries(data.disks).map(([key, value], index) => <tr key={key}><td>{index + 1}</td><td>{key === "images" ? "Ảnh" : "Mô hình"}</td><td>{value ? `${(value.free_bytes / 1024 ** 3).toFixed(1)} GiB · ${value.free_percent}%` : "Không khả dụng"}</td></tr>)}</tbody></table></div><small>Cập nhật: {new Date(data.observed_at).toLocaleString("vi-VN")}</small></>}
  </section>;
}
