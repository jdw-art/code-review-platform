import { RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { matchPath, useLocation } from "react-router-dom";

const routeTitleMap = [
  { path: "/dashboard", title: "欢迎回来" },
  { path: "/projects", title: "项目管理" },
  { path: "/projects/:projectId/agent", title: "项目管理" },
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
  mustChangePassword,
  onRefresh,
}: {
  username: string;
  nickname: string | null;
  mustChangePassword: boolean;
  onLogout: () => Promise<void>;
  onRefresh?: () => Promise<void> | void;
}) {
  const location = useLocation();
  const [refreshing, setRefreshing] = useState(false);
  const routeTitle = resolveRouteTitle(location.pathname);

  async function handleRefresh() {
    if (onRefresh === undefined) {
      return;
    }
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <header className="border-b border-slate-200/50 bg-white/60 px-8 py-3 backdrop-blur-[2px]">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-400">
            管理台
          </span>
          <span className="font-mono text-slate-300">/</span>
          <span className="rounded-[4px] border border-indigo-100 bg-indigo-50/50 px-2 py-0.5 text-xs font-bold text-indigo-700">
            {routeTitle}
          </span>
          {mustChangePassword ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700">
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>账号需要先修改密码</span>
            </span>
          ) : null}
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void handleRefresh()}
            title="刷新系统数据"
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-500 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-colors hover:bg-slate-50 hover:text-slate-700"
          >
            <RefreshCw className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} />
            <span className="text-[10px]">同步状态</span>
          </button>
        </div>
      </div>
    </header>
  );
}
