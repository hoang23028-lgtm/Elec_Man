"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { activateModel, getEvaluation, getModels, registerModel, type Evaluation, type ModelInput, type ModelRecord } from "@/services/administration";

const emptyInput: ModelInput = { model_name: "", model_type: "digit_reader", version: "", file_path: "", sha256: "", metrics: {} };
const percent = (value: number | null) => value === null ? "Not available" : `${Math.round(value * 1000) / 10}%`;

export function ModelOperations({ csrfToken }: { csrfToken: string }) {
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [input, setInput] = useState<ModelInput>(emptyInput);
  const [metricsJson, setMetricsJson] = useState("{}");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    try {
      const [modelRows, summary] = await Promise.all([getModels(), getEvaluation()]);
      setModels(modelRows);
      setEvaluation(summary);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load model operations.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const metrics = JSON.parse(metricsJson) as Record<string, unknown>;
      await registerModel({ ...input, metrics }, csrfToken);
      setInput(emptyInput);
      setMetricsJson("{}");
      setNotice("Model bundle verified and registered in TESTING status.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to register model. Check the metrics JSON.");
    } finally {
      setSaving(false);
    }
  }

  async function activate(record: ModelRecord) {
    if (!window.confirm(`Activate ${record.model_name} ${record.version}? The worker must be restarted to load a new runtime bundle.`)) return;
    setSaving(true);
    setError(null);
    try {
      await activateModel(record.id, csrfToken);
      setNotice("Registry activation saved. Restart the worker only after its adapter is configured for this bundle.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to activate model.");
    } finally {
      setSaving(false);
    }
  }

  return <section className="panel full-span" aria-labelledby="models-title">
    <div className="section-heading"><div><p className="eyebrow">Model lifecycle</p><h2 id="models-title">Registry and evaluation</h2></div><span className="badge active">Human approval required</span></div>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="notice" role="status">{notice}</p>}
    <div className="metrics evaluation-metrics"><div><strong>{evaluation?.confirmed_samples ?? "—"}</strong><span>Confirmed samples</span></div><div><strong>{percent(evaluation?.customer_exact_accuracy ?? null)}</strong><span>Customer exact</span></div><div><strong>{percent(evaluation?.meter_exact_accuracy ?? null)}</strong><span>Reading exact</span></div><div><strong>{percent(evaluation?.meter_digit_accuracy ?? null)}</strong><span>Digit accuracy</span></div></div>
    <p className="muted">Metrics use only human-confirmed production samples. They are not a held-out test-set accuracy claim.</p>
    {models.length === 0 ? <p className="muted">No deployable model bundle has been registered. The current OCR baseline is bundled with the worker and remains review-only.</p> : <div className="table-wrap"><table><thead><tr><th>Model</th><th>Type</th><th>Version</th><th>Status</th><th>Action</th></tr></thead><tbody>{models.map((record) => <tr key={record.id}><td>{record.model_name}<small>{record.file_path}</small></td><td>{record.model_type}</td><td>{record.version}</td><td><span className={`badge ${record.status === "ACTIVE" ? "active" : ""}`}>{record.status}</span></td><td><button type="button" onClick={() => void activate(record)} disabled={saving || record.status === "ACTIVE"}>Activate</button></td></tr>)}</tbody></table></div>}
    <details className="registration"><summary>Register a verified model bundle</summary><form className="settings-form" onSubmit={submit}><div className="settings-grid"><div className="setting-field"><label htmlFor="model-name">Model name</label><input id="model-name" value={input.model_name} onChange={(event) => setInput((current) => ({ ...current, model_name: event.target.value }))} required /></div><div className="setting-field"><label htmlFor="model-type">Model type</label><input id="model-type" value={input.model_type} onChange={(event) => setInput((current) => ({ ...current, model_type: event.target.value }))} required /></div><div className="setting-field"><label htmlFor="model-version">Version</label><input id="model-version" value={input.version} onChange={(event) => setInput((current) => ({ ...current, version: event.target.value }))} placeholder="1.0.0" required /></div><div className="setting-field"><label htmlFor="model-file">Relative file path under MODELS_ROOT</label><input id="model-file" value={input.file_path} onChange={(event) => setInput((current) => ({ ...current, file_path: event.target.value }))} placeholder="digit_reader/v1/model.onnx" required /></div><div className="setting-field"><label htmlFor="model-sha">SHA-256</label><input id="model-sha" minLength={64} maxLength={64} value={input.sha256} onChange={(event) => setInput((current) => ({ ...current, sha256: event.target.value }))} required /></div><div className="setting-field"><label htmlFor="model-metrics">Metrics JSON</label><input id="model-metrics" value={metricsJson} onChange={(event) => setMetricsJson(event.target.value)} required /></div></div><button type="submit" disabled={saving}>{saving ? "Verifying…" : "Verify and register"}</button></form></details>
  </section>;
}
