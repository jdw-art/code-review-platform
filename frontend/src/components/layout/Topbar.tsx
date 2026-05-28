import { LogOut, ShieldAlert, UserCircle2 } from "lucide-react";
import { useState } from "react";

/**
 * Topbar 负责承载当前登录态信息和退出动作，避免页面各自实现一套头部。
 */
export function Topbar({
  username,
  nickname,
  mustChangePassword,
  onLogout,
}: {
  username: string;
  nickname: string | null;
  mustChangePassword: boolean;
  onLogout: () => Promise<void>;
}) {
  const [submitting, setSubmitting] = useState(false);
  const displayName = nickname?.trim() || username;

  async function handleLogout() {
    setSubmitting(true);
    try {
      await onLogout();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-slate-500">
          管理台
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-slate-900">欢迎回来</h2>
        <p className="mt-2 text-sm text-slate-600">
          当前工作区已接入认证上下文、菜单树和基础后台壳子。
        </p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {mustChangePassword ? (
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
            <ShieldAlert className="h-4 w-4" />
            账号需要先修改密码
          </div>
        ) : null}
        <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm">
          <UserCircle2 className="h-5 w-5 text-cyan-700" />
          <span>{displayName}</span>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          disabled={submitting}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <LogOut className="h-4 w-4" />
          {submitting ? "退出中..." : "退出登录"}
        </button>
      </div>
    </header>
  );
}
