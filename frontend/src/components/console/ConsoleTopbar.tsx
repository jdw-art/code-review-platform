import { LogOut, ShieldAlert } from "lucide-react";
import { useState } from "react";

export function ConsoleTopbar({
  mustChangePassword,
  onLogout,
}: {
  mustChangePassword: boolean;
  onLogout: () => Promise<void>;
}) {
  const [submitting, setSubmitting] = useState(false);

  async function handleLogout() {
    setSubmitting(true);
    try {
      await onLogout();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/90 backdrop-blur">
      <div className="flex items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-mono uppercase tracking-[0.28em] text-slate-400">管理台</span>
          <span className="text-slate-300">/</span>
          <span className="rounded-md border border-indigo-100 bg-indigo-50 px-2 py-1 font-semibold text-indigo-700">
            审查控制台
          </span>
          {mustChangePassword ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>账号需要先修改密码</span>
            </span>
          ) : null}
        </div>
        <button
          type="button"
          onClick={handleLogout}
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>{submitting ? "退出中..." : "退出登录"}</span>
        </button>
      </div>
    </header>
  );
}
