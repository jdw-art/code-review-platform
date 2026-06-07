import axios from "axios";
import {
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import { startTransition, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import type { ApiErrorResponse } from "../../lib/api/types";
import { useAuth } from "../../lib/auth/auth-context";

function readErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    return error.response?.data.message ?? fallback;
  }
  return fallback;
}

/**
 * 登录页按前端原型完整迁移，同时继续承载真实登录与首次登录改密流。
 */
export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { changePassword, login, mustChangePassword, status } = useAuth();
  const [form, setForm] = useState({
    username: "admin",
    password: "admin2026",
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") {
      return;
    }

    const from =
      typeof location.state === "object" &&
      location.state !== null &&
      "from" in location.state &&
      typeof location.state.from === "string"
        ? location.state.from
        : "/dashboard";

    startTransition(() => {
      navigate(from, { replace: true });
    });
  }, [location.state, navigate, status]);

  function updateField(field: "username" | "password", value: string) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function updatePasswordField(
    field: "current_password" | "new_password",
    value: string
  ) {
    setPasswordForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleLoginSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.username.trim()) {
      setErrorMessage("请输入用户名");
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await login(form);
    } catch (error) {
      setErrorMessage(readErrorMessage(error, "登录失败，请稍后再试。"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleChangePasswordSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await changePassword(passwordForm);
      setPasswordForm({
        current_password: "",
        new_password: "",
      });
      setSuccessMessage("密码修改成功，请使用新密码重新登录。");
    } catch (error) {
      setErrorMessage(readErrorMessage(error, "修改密码失败，请稍后再试。"));
    } finally {
      setSubmitting(false);
    }
  }

  const showPasswordChangeForm = status === "password_change_required" || mustChangePassword;

  if (showPasswordChangeForm) {
    return (
      <main className="min-h-screen bg-[#fafafa] px-6 py-10 text-slate-900">
        <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-md items-center">
          <section className="w-full rounded-2xl border border-slate-200/60 bg-white p-8 shadow-[0_8px_30px_rgb(0,0,0,0.02)]">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-indigo-50 p-3 text-indigo-600">
                <KeyRound className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-2xl font-semibold text-slate-900">
                  首次登录需要先修改密码
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  后端安全策略已限制管理接口访问，请先完成改密。
                </p>
              </div>
            </div>

            {errorMessage ? (
              <div className="mt-6 rounded-xl border border-rose-100 bg-rose-50/60 p-3 text-xs font-medium text-rose-700">
                {errorMessage}
              </div>
            ) : null}
            {successMessage ? (
              <div className="mt-6 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3 text-xs font-medium text-emerald-700">
                {successMessage}
              </div>
            ) : null}

            <form className="mt-8 space-y-4" onSubmit={handleChangePasswordSubmit}>
              <div className="space-y-1.5">
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  当前密码
                </label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(event) =>
                      updatePasswordField("current_password", event.target.value)
                    }
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/40 py-2.5 pl-9 pr-4 text-xs font-semibold text-slate-800 transition-all hover:bg-slate-50 focus:border-indigo-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-indigo-500/25"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  新密码
                </label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                    <KeyRound className="h-4 w-4" />
                  </div>
                  <input
                    type="password"
                    value={passwordForm.new_password}
                    onChange={(event) =>
                      updatePasswordField("new_password", event.target.value)
                    }
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/40 py-2.5 pl-9 pr-4 text-xs font-semibold text-slate-800 transition-all hover:bg-slate-50 focus:border-indigo-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-indigo-500/25"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-[0_2px_10px_rgba(99,102,241,0.15)] transition-all hover:bg-indigo-700 hover:shadow-[0_4px_16px_rgba(99,102,241,0.2)] disabled:pointer-events-none disabled:opacity-50"
              >
                <span>{submitting ? "提交中..." : "修改密码"}</span>
              </button>
            </form>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen w-full overflow-hidden bg-[#fafafa] p-6 text-slate-900 selection:bg-indigo-200 selection:text-indigo-900">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.015)_1px,transparent_1px)] bg-[size:32px_32px]" />
      <div className="pointer-events-none absolute left-1/2 top-1/4 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-indigo-500/5 blur-3xl" />

      <div className="relative z-10 flex min-h-[calc(100vh-3rem)] items-center justify-center">
        <section className="w-full max-w-md rounded-2xl border border-slate-200/60 bg-white p-8 shadow-[0_8px_30px_rgb(0,0,0,0.02)]">
          <div className="mb-6 flex justify-center">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/40 bg-slate-50 px-2 py-0.5 font-mono text-[10px] tracking-tight text-slate-500">
              <Sparkles className="h-3 w-3 text-indigo-500" />
              <span>Platform Auth Node</span>
            </div>
          </div>

          <div className="mb-8 space-y-2 text-center">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              AI Code Review Console
            </h1>
            <p className="mx-auto max-w-[280px] text-xs font-light leading-relaxed text-slate-400">
              极简、安全、端到端的全功能代码分析与管理平台
            </p>
          </div>

          {errorMessage ? (
            <div className="mb-5 flex items-center gap-2 rounded-xl border border-red-100 bg-red-50/60 p-3 text-xs font-medium text-red-700">
              <div className="h-1 w-1 rounded-full bg-red-500" />
              <span>{errorMessage}</span>
            </div>
          ) : null}

          {successMessage ? (
            <div className="mb-5 flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3 text-xs font-medium text-emerald-700">
              <div className="h-1 w-1 rounded-full bg-emerald-500" />
              <span>{successMessage}</span>
            </div>
          ) : null}

          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="login-username"
                className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500"
              >
                用户名
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  <User className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  id="login-username"
                  type="text"
                  required
                  value={form.username}
                  onChange={(event) => {
                    updateField("username", event.target.value);
                    if (errorMessage) {
                      setErrorMessage(null);
                    }
                  }}
                  placeholder="请输入管理员或工程师账号"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/40 py-2.5 pl-9 pr-4 text-xs font-semibold text-slate-800 transition-all hover:bg-slate-50 focus:border-indigo-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-indigo-500/25"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="login-password"
                  className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500"
                >
                  密码
                </label>
                <button
                  type="button"
                  className="cursor-pointer text-[10px] font-medium text-indigo-600 transition-colors hover:text-indigo-700"
                >
                  忘记密码？
                </button>
              </div>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                  <Lock className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={form.password}
                  onChange={(event) => {
                    updateField("password", event.target.value);
                    if (errorMessage) {
                      setErrorMessage(null);
                    }
                  }}
                  placeholder="请输入您的登录密码"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/40 py-2.5 pl-9 pr-9 text-xs font-semibold text-slate-800 transition-all hover:bg-slate-50 focus:border-indigo-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-indigo-500/25"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between rounded-xl border border-slate-200/50 bg-slate-50 px-3 py-2.5 text-[11px]">
              <span className="font-mono text-slate-400">预设工作账号:</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setForm({
                      username: "admin",
                      password: "admin2026",
                    });
                    setErrorMessage(null);
                  }}
                  className={`cursor-pointer rounded-md border px-2 py-0.5 text-[10px] transition-all ${
                    form.username === "admin"
                      ? "border-slate-300 bg-white font-extrabold text-slate-800 shadow-sm"
                      : "border-transparent bg-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  超级管理员
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setForm({
                      username: "developer",
                      password: "dev2026",
                    });
                    setErrorMessage(null);
                  }}
                  className={`cursor-pointer rounded-md border px-2 py-0.5 text-[10px] transition-all ${
                    form.username === "developer"
                      ? "border-slate-300 bg-white font-extrabold text-slate-800 shadow-sm"
                      : "border-transparent bg-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  开发工程师
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="group flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  defaultChecked
                  className="h-3.5 w-3.5 rounded border-slate-200 text-indigo-600 focus:ring-indigo-500/20"
                />
                <span className="select-none text-[11px] text-slate-400 transition-colors group-hover:text-slate-600">
                  30 天内保持登录状态
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={submitting || status === "loading"}
              className="mt-4 flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-[0_2px_10px_rgba(99,102,241,0.15)] transition-all hover:bg-indigo-700 hover:shadow-[0_4px_16px_rgba(99,102,241,0.2)] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-50"
            >
              {submitting ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
              ) : (
                <>
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>进入控制台</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-8 flex items-center justify-between border-t border-slate-100 pt-4 font-mono text-[9px] tracking-tight text-slate-400">
            <span>CONSOLE SYSTEM v2.0</span>
            <span>SECURED TRANSIT</span>
          </div>
        </section>
      </div>
    </main>
  );
}
