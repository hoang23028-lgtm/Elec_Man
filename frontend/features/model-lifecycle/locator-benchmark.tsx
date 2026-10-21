const object = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
const metric = (value: unknown, percent = false) => typeof value === "number" && Number.isFinite(value) ? percent ? `${(value * 100).toFixed(1)}%` : `${value.toFixed(1)} ms` : "Chưa đo";

export function LocatorBenchmark({ value }: { value: unknown }) {
  const data = object(value);
  if (!Object.keys(data).length) return null;
  return <details><summary>So sánh Ridge / MobileNetV3</summary><p className="muted">Cùng snapshot, không tự chọn hoặc kích hoạt mô hình. IoU toàn luồng định vị; không cung cấp vùng thật cho suy luận.</p>
    {(["validation", "holdout"] as const).map(split => <div key={split}><p>{split === "validation" ? "Chọn trọng số / chẩn đoán" : data.independent_holdout === true ? "Kiểm tra độc lập" : "Chưa có kiểm tra độc lập"}</p><div className="table-wrap"><table><thead><tr><th>STT</th><th>Kiến trúc</th><th>Mẫu</th><th>IoU công tơ</th><th>IoU vùng số</th><th>p95 định vị</th></tr></thead><tbody>{["ridge", "mobilenetv3"].map((kind, index) => { const row = object(object(data[split])[kind]); return <tr key={kind}><td>{index + 1}</td><td>{kind === "ridge" ? "Ridge" : "MobileNetV3"}</td><td>{typeof row.samples === "number" ? row.samples : 0}</td><td>{metric(row.meter_mean_iou, true)}</td><td>{metric(row.reading_mean_iou, true)}</td><td>{metric(row.p95_ms)}</td></tr>; })}</tbody></table></div></div>)}
  </details>;
}
