import { Outlet } from "react-router-dom";

import { useAuth } from "../../lib/auth/auth-context";
import { SidebarNav } from "./SidebarNav";
import { Topbar } from "./Topbar";

/**
 * AppShell 承载后台统一布局，把菜单、顶部信息和页面内容区拼成一个可复用框架。
 */
export function AppShell() {
  const { menuTree, mustChangePassword, logout, status, user } = useAuth();

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
        <div className="rounded-3xl border border-slate-200 bg-white px-8 py-6 text-sm text-slate-600 shadow-sm">
          正在初始化后台会话...
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 lg:flex">
      <SidebarNav menus={menuTree} />
      <div className="flex-1 px-6 py-6 lg:px-10">
        <Topbar
          username={user?.username ?? "unknown"}
          nickname={user?.nickname ?? null}
          mustChangePassword={mustChangePassword}
          onLogout={logout}
        />
        <main className="mt-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
