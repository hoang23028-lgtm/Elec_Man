"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { login, logout, registerAccount, restoreSession } from "@/services/auth";
import { ApiError } from "@/services/http";
import { canLeavePage } from "@/hooks/use-leave-guard";
import type { LoginInput, RegistrationFormInput, UserRole } from "@/types/auth";

export function useAuthentication(resetPage: () => void) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [sessionUsername, setSessionUsername] = useState<string | null>(null);
  const [sessionRole, setSessionRole] = useState<UserRole | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [showPasswords, setShowPasswords] = useState(false);
  const loginTriggerRef = useRef<HTMLButtonElement>(null);
  const loginModalRef = useRef<HTMLElement>(null);
  const loginForm = useForm<LoginInput>();
  const registrationForm = useForm<RegistrationFormInput>();
  const {
    register: registerLogin,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors, isSubmitting: isLoggingIn },
  } = loginForm;
  const {
    register: registerRegistration,
    handleSubmit: handleRegistrationSubmit,
    reset: resetRegistration,
    formState: { errors: registrationErrors, isSubmitting: isRegistering },
  } = registrationForm;

  const closeLogin = useCallback(() => {
    setLoginOpen(false);
    setAuthMode("login");
    setShowPasswords(false);
    setError(null);
    window.requestAnimationFrame(() => loginTriggerRef.current?.focus());
  }, []);

  useEffect(() => {
    let alive = true;
    void restoreSession().then((session) => {
      if (!alive) return;
      setSessionUsername(session.username);
      setSessionRole(session.role);
      setCsrfToken(session.csrf_token); setExpiresAt(session.expires_at);
    }).catch((reason) => {
      if (alive && !(reason instanceof ApiError && reason.status === 401)) setError("Không thể kiểm tra phiên đăng nhập. Bạn có thể đăng nhập lại.");
    }).finally(() => { if (alive) setAuthLoading(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!csrfToken || sessionExpired) return;
    function expire() {
      setSessionExpired(true); setLoginOpen(true); setAuthMode("login");
      setMessage("Phiên đăng nhập đã hết hạn. Đăng nhập lại cùng tài khoản để tiếp tục; bản nháp vẫn được giữ trên trang này.");
    }
    window.addEventListener("session-expired", expire);
    const timer = expiresAt ? window.setTimeout(expire, Math.max(0, Date.parse(expiresAt) - Date.now())) : undefined;
    return () => { window.removeEventListener("session-expired", expire); if (timer !== undefined) window.clearTimeout(timer); };
  }, [csrfToken, expiresAt, sessionExpired]);

  useEffect(() => {
    if (!loginOpen) return;
    function handleModalKeyboard(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeLogin();
        return;
      }
      if (event.key !== "Tab") return;
      const controls = loginModalRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      );
      if (!controls?.length) return;
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", handleModalKeyboard);
    return () => window.removeEventListener("keydown", handleModalKeyboard);
  }, [closeLogin, loginOpen]);

  async function submitLogin(values: LoginInput) {
    setError(null);
    setMessage(null);
    try {
      if (sessionExpired && sessionUsername && values.username !== sessionUsername) {
        setError("Hãy đăng nhập lại cùng tài khoản để giữ bản nháp, hoặc đăng xuất để trở về Tổng quan trước khi đổi tài khoản."); return;
      }
      const result = await login(values);
      // This value is not a credential. It remains only in React memory for
      // future state-changing requests and is never written to localStorage.
      setCsrfToken(result.csrf_token);
      setExpiresAt(result.expires_at);
      setSessionUsername(result.username);
      setSessionRole(result.role);
      setSessionExpired(false);
      setLoginOpen(false);
      if (!sessionExpired) {
        resetPage();
        window.history.replaceState(null, "", "#dashboard");
      }
      setMessage(result.role === "ADMIN" || result.role === "SUPER_ADMIN"
        ? "Đăng nhập thành công. Hãy tải ảnh, theo dõi lô dữ liệu và kiểm duyệt từng chỉ số."
        : "Đăng nhập thành công với quyền chỉ xem Dashboard.");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể đăng nhập.",
      );
    }
  }

  async function submitRegistration(values: RegistrationFormInput) {
    setError(null);
    setMessage(null);
    try {
      const result = await registerAccount({
        username: values.username,
        password: values.password,
      });
      setLoginOpen(false);
      setAuthMode("login");
      setMessage(result.message);
      window.requestAnimationFrame(() => document.getElementById("auth-trigger")?.focus());
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Không thể gửi yêu cầu đăng ký.",
      );
    }
  }

  async function signOut() {
    if (!csrfToken) return;
    if (!canLeavePage()) return;
    try {
      if (!sessionExpired) await logout(csrfToken);
      setCsrfToken(null);
      setExpiresAt(null); setSessionExpired(false); setSessionUsername(null);
      setSessionRole(null);
      setLoginOpen(false);
      resetPage();
      window.history.replaceState(null, "", window.location.pathname);
      setMessage("Đã đăng xuất.");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Không thể đăng xuất.",
      );
    }
  }

  function switchAuthMode(mode: "login" | "register") {
    if (mode === "register") resetRegistration();
    setAuthMode(mode);
    setShowPasswords(false);
    setError(null);
  }

  return { message, error, csrfToken, authLoading, sessionExpired, sessionRole, loginOpen, setLoginOpen, authMode, setAuthMode, showPasswords, setShowPasswords, setError, loginTriggerRef, loginModalRef, registerLogin, handleLoginSubmit, loginErrors, isLoggingIn, registerRegistration, handleRegistrationSubmit, registrationErrors, isRegistering, closeLogin, submitLogin, submitRegistration, signOut, switchAuthMode };
}
