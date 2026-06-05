import { LogOut, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { matchPath, useLocation } from "react-router-dom";

const routeTitleMap = [
  { path: "/dashboard", title: "欢迎回来" },
  { path: "/projects", title: "项目管理" },
  { path: "/project-templates", title: "项目模板管理" },
  { path: "/models", title: "模型管理" },
  { path: "/notification-bots", title: "通知机器人配置" },
  { path: "/review-records", title: "智能审查记录" },
  { path: "/review-records/:reviewRecordId", title: "智能审查记录" },
  { path: "/member-analytics", title: "团队成员分析" },
  { path: "/system/users", title: "系统用户中心" },
  { path: "/system/roles", title: "智能角色矩阵" },
  { path: "/audit-logs", title: "系统审计日志" },
] as const;

function resolveRouteTitle(pathname: string) {
  const matchedRoute = routeTitleMap.find(({ path }) =>
    matchPath({ path, end: true }, pathname)
  );

  return matchedRoute?.title ?? "欢迎回来";
}

export function ConsoleTopbar({
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
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const displayName = nickname?.trim() || username;
  const routeTitle = resolveRouteTitle(location.pathname);

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
            {routeTitle}
          </span>
          {mustChangePassword ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>账号需要先修改密码</span>
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600">
            {displayName}
          </span>
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
      </div>
    </header>
  );
}
