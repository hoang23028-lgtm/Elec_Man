"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { getSettings, saveSettings, type Setting } from "@/services/administration";

const labels: Record<string, string> = {
  confidence_ok_threshold: "OK confidence threshold",
  confidence_review_threshold: "Review confidence threshold",
  max_upload_size_mb: "Maximum upload size (MB)",
  max_retry_count: "Maximum retry count",
  data_retention_days: "Data retention planning (days)",
  worker_poll_interval_seconds: "Worker polling interval (seconds)",
};

export function SystemSettings({ csrfToken }: { csrfToken: string }) {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    try {
      const rows = await getSettings();
      setSettings(rows);
      setDrafts(Object.fromEntries(rows.map((row) => [row.key, String(row.value)])));
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load settings.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    const values = Object.fromEntries(Object.entries(drafts).map(([key, value]) => [key, Number(value)]));
    if (Object.values(values).some((value) => !Number.isFinite(value))) {
      setError("Every setting must be a valid number.");
      setSaving(false);
      return;
    }
    try {
      const rows = await saveSettings(values, csrfToken);
      setSettings(rows);
      setNotice("Settings saved and recorded in the audit history.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save settings.");
    } finally {
      setSaving(false);
    }
  }

  return <section className="panel full-span" aria-labelledby="settings-title">
    <div className="section-heading"><div><p className="eyebrow">Administration</p><h2 id="settings-title">System settings</h2></div><span className="badge">Audited changes</span></div>
    <p className="muted">Operational policy values are stored centrally. Deployment-level limits take effect after the related service is restarted.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p className="notice" role="status">{notice}</p>}
    {settings.length === 0 && !error ? <p className="muted" role="status">Loading settings…</p> : <form className="settings-form" onSubmit={submit}>
      <div className="settings-grid">{settings.map((setting) => <div className="setting-field" key={setting.key}><label htmlFor={`setting-${setting.key}`}>{labels[setting.key] ?? setting.key}</label><input id={`setting-${setting.key}`} type="number" step={setting.key.includes("confidence") ? "0.01" : setting.key.includes("seconds") ? "0.1" : "1"} value={drafts[setting.key] ?? ""} onChange={(event) => setDrafts((current) => ({ ...current, [setting.key]: event.target.value }))} required /><small>{setting.description}</small></div>)}</div>
      <button type="submit" disabled={saving}>{saving ? "Saving settings…" : "Save settings"}</button>
    </form>}
  </section>;
}
