import { Outlet } from "react-router-dom";

import { useAuth } from "../../lib/auth/auth-context";
import { ConsoleShell } from "../console/ConsoleShell";

/**
 * AppShell 承载后台统一布局，把菜单、顶部信息和页面内容区拼成一个可复用框架。
 */
export function AppShell() {
  const { menuTree, logout, mustChangePassword, roles, status, user } = useAuth();

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
        <div className="rounded-3xl border border-slate-200 bg-white px-8 py-6 text-sm text-slate-600 shadow-sm">
          正在初始化后台会话...
        </div>
      </main>
    );
  }

  const roleLabel = roles[0]?.name ?? "超级管理员";

  return (
    <ConsoleShell
      menus={menuTree}
      username={user?.username ?? "unknown"}
      roleLabel={roleLabel}
      mustChangePassword={mustChangePassword}
      onLogout={logout}
    >
      <Outlet />
    </ConsoleShell>
  );
}
