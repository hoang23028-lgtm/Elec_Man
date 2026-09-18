"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";

import { login, logout } from "@/services/auth";
import type { LoginInput } from "@/types/auth";
import { FolderUpload } from "@/components/folder-upload";
import { ResultReview } from "@/components/result-review";
import { BatchOverview } from "@/components/batch-overview";
import { DashboardSummary } from "@/components/dashboard-summary";
import { AuditHistory } from "@/components/audit-history";
import { ModelOperations } from "@/components/model-operations";
import { SystemSettings } from "@/components/system-settings";

export default function HomePage() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginInput>();

  async function submit(values: LoginInput) {
    setError(null);
    setMessage(null);
    try {
      const result = await login(values);
      // This value is not a credential. It remains only in React memory for
      // future state-changing requests and is never written to localStorage.
      setCsrfToken(result.csrf_token);
      setMessage("Signed in. Upload images, monitor batches, then review each reading.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in.");
    }
  }

  async function signOut() { if (!csrfToken) return; try { await logout(csrfToken); setCsrfToken(null); setMessage("Signed out."); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to sign out."); } }

  return <main><div className="shell"><header><div className="section-heading"><div><p className="eyebrow">Internal operations</p><h1 id="page-title">Electricity Meter Review</h1><p className="muted">Upload, monitor, and verify meter readings in one place.</p></div>{csrfToken && <button className="secondary" type="button" onClick={() => void signOut()}>Sign out</button>}</div></header>{!csrfToken && <section className="panel login" aria-labelledby="page-title"><form onSubmit={handleSubmit(submit)} noValidate><label htmlFor="username">Username</label><input id="username" autoComplete="username" {...register("username", { required: "Username is required." })} /><span className="error">{errors.username?.message}</span><label htmlFor="password">Password</label><input id="password" type="password" autoComplete="current-password" {...register("password", { required: "Password is required." })} /><span className="error">{errors.password?.message}</span><button type="submit" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Sign in"}</button></form></section>}{csrfToken && <div className="workspace"><DashboardSummary csrfToken={csrfToken} /><FolderUpload csrfToken={csrfToken} /><BatchOverview /><ResultReview csrfToken={csrfToken} /><SystemSettings csrfToken={csrfToken} /><ModelOperations csrfToken={csrfToken} /><AuditHistory /></div>}{error && <p className="error" role="alert">{error}</p>}{message && <p className="notice" role="status">{message}</p>}</div></main>;
}
