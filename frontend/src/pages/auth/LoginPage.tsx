import axios from "axios";
import { KeyRound, LockKeyhole, UserRound } from "lucide-react";
import { startTransition, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import type { ApiErrorResponse } from "../../lib/api/types";
import { useAuth } from "../../lib/auth/auth-context";

const presetAccounts = [
  {
    role: "超级管理员",
    username: "admin",
    hint: "全量管理项目、模型、系统配置与审计日志。",
  },
  {
    role: "开发工程师",
    username: "reviewer",
    hint: "聚焦项目接入、审查记录追踪与团队协作分析。",
  },
] as const;

function readErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    return error.response?.data.message ?? fallback;
  }
  return fallback;
}

/**
 * LoginPage 统一承载普通登录与首次登录强制改密两种认证流。
 */
export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { changePassword, login, mustChangePassword, status } = useAuth();
  const [form, setForm] = useState({
    username: "admin",
    password: "",
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
  });
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
    setSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const result = await login(form);
      if (!result.mustChangePassword) {
        startTransition(() => {
          navigate("/dashboard", { replace: true });
        });
      }
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

  return (
    <main className="min-h-screen bg-[linear-gradient(135deg,_#e2e8f0_0%,_#f8fafc_45%,_#cffafe_100%)] px-6 py-10 text-slate-900">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="overflow-hidden rounded-[2rem] border border-white/60 bg-slate-950 px-8 py-10 text-white shadow-[0_30px_90px_rgba(15,23,42,0.18)]">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-200/85">Console Login</p>
          <h1 className="mt-4 text-4xl font-semibold">AI Code Review Console</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
            从这里进入智能审查控制台。当前认证流已接入 JWT 登录、refresh token 续期、RBAC 菜单初始化，以及首次登录强制改密分支。
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {presetAccounts.map((account) => (
              <button
                key={account.role}
                type="button"
                onClick={() => updateField("username", account.username)}
                className="rounded-3xl border border-white/10 bg-white/5 p-5 text-left transition hover:border-cyan-300/50 hover:bg-white/10"
              >
                <p className="text-sm font-medium text-white">{account.role}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.24em] text-cyan-200/85">
                  {account.username}
                </p>
                <p className="mt-3 text-sm leading-6 text-slate-300">{account.hint}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_24px_70px_rgba(148,163,184,0.18)]">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-cyan-50 p-3 text-cyan-700">
              {showPasswordChangeForm ? (
                <KeyRound className="h-5 w-5" />
              ) : (
                <UserRound className="h-5 w-5" />
              )}
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-slate-900">
                {showPasswordChangeForm ? "首次登录需要先修改密码" : "登录后台"}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {showPasswordChangeForm
                  ? "后端安全策略已限制管理接口访问，请先完成改密。"
                  : "请输入账号密码，进入后台工作区。"}
              </p>
            </div>
          </div>

          {errorMessage ? (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}
          {successMessage ? (
            <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {successMessage}
            </div>
          ) : null}

          {showPasswordChangeForm ? (
            <form className="mt-8 space-y-5" onSubmit={handleChangePasswordSubmit}>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">
                  当前密码
                </span>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <LockKeyhole className="h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    value={passwordForm.current_password}
                    onChange={(event) =>
                      updatePasswordField("current_password", event.target.value)
                    }
                    className="w-full bg-transparent text-sm outline-none"
                  />
                </div>
              </label>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">
                  新密码
                </span>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <KeyRound className="h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    value={passwordForm.new_password}
                    onChange={(event) =>
                      updatePasswordField("new_password", event.target.value)
                    }
                    className="w-full bg-transparent text-sm outline-none"
                  />
                </div>
              </label>
              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-2xl bg-slate-950 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "提交中..." : "修改密码"}
              </button>
            </form>
          ) : (
            <form className="mt-8 space-y-5" onSubmit={handleLoginSubmit}>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">
                  用户名
                </span>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <UserRound className="h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    value={form.username}
                    onChange={(event) => updateField("username", event.target.value)}
                    className="w-full bg-transparent text-sm outline-none"
                  />
                </div>
              </label>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-700">
                  密码
                </span>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <LockKeyhole className="h-4 w-4 text-slate-400" />
                  <input
                    type="password"
                    value={form.password}
                    onChange={(event) => updateField("password", event.target.value)}
                    className="w-full bg-transparent text-sm outline-none"
                  />
                </div>
              </label>
              <button
                type="submit"
                disabled={submitting || status === "loading"}
                className="w-full rounded-2xl bg-slate-950 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "进入中..." : "进入控制台"}
              </button>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}
