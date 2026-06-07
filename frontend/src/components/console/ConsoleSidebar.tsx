import { useEffect, useMemo, useState } from "react";
import {
  BadgeCheck,
  Bot,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileJson,
  FolderCode,
  KeyRound,
  LayoutDashboard,
  LogOut,
  ScrollText,
  ShieldAlert,
  UserCheck,
  Users,
  BookmarkCheck,
} from "lucide-react";
import { Link, matchPath, useLocation } from "react-router-dom";

import type { MenuNode } from "../../lib/api/types";

type NavItem = {
  id: string;
  text: string;
  icon: typeof LayoutDashboard;
  path?: string;
  badge?: string;
  children?: Array<{
    id: string;
    text: string;
    icon: typeof LayoutDashboard;
    path: string;
  }>;
};

function hasMenuPath(menus: MenuNode[], path: string): boolean {
  return menus.some((menu) => {
    if (menu.path === path) {
      return true;
    }
    return hasMenuPath(menu.children, path);
  });
}

function buildPrototypeNav(menus: MenuNode[]) {
  const nav: NavItem[] = [
    {
      id: "dashboard",
      text: "仪表盘",
      icon: LayoutDashboard,
      path: "/dashboard",
    },
  ];

  if (hasMenuPath(menus, "/projects")) {
    nav.push({
      id: "projects",
      text: "项目管理",
      icon: FolderCode,
      path: "/projects",
      badge: "6",
    });
  }

  if (hasMenuPath(menus, "/project-templates")) {
    nav.push({
      id: "templates",
      text: "项目模板管理",
      icon: FileJson,
      path: "/project-templates",
    });
  }

  if (hasMenuPath(menus, "/models")) {
    nav.push({
      id: "models",
      text: "模型管理",
      icon: Cpu,
      path: "/models",
      badge: "NEW",
    });
  }

  if (hasMenuPath(menus, "/notification-bots")) {
    nav.push({
      id: "robots",
      text: "通知机器人",
      icon: Bot,
      path: "/notification-bots",
    });
  }

  if (hasMenuPath(menus, "/review-records")) {
    nav.push({
      id: "records",
      text: "审查记录",
      icon: BookmarkCheck,
      path: "/review-records",
      badge: "30",
    });
  }

  if (hasMenuPath(menus, "/member-analytics")) {
    nav.push({
      id: "members",
      text: "成员分析",
      icon: Users,
      path: "/member-analytics",
    });
  }

  const permissionChildren: NavItem["children"] = [];

  if (hasMenuPath(menus, "/system/users")) {
    permissionChildren.push({
      id: "users",
      text: "用户管理",
      icon: UserCheck,
      path: "/system/users",
    });
  }

  if (hasMenuPath(menus, "/system/roles")) {
    permissionChildren.push({
      id: "roles",
      text: "角色管理",
      icon: ShieldAlert,
      path: "/system/roles",
    });
  }

  if (permissionChildren.length > 0) {
    nav.push({
      id: "permissions",
      text: "权限管理",
      icon: KeyRound,
      children: permissionChildren,
    });
  }

  if (hasMenuPath(menus, "/audit-logs")) {
    nav.push({
      id: "logs",
      text: "系统日志",
      icon: ScrollText,
      path: "/audit-logs",
    });
  }

  return nav;
}

function isPathActive(currentPathname: string, path: string) {
  if (path === "/projects") {
    return (
      matchPath({ path: "/projects", end: true }, currentPathname) !== null ||
      matchPath({ path: "/projects/:projectId/agent", end: false }, currentPathname) !== null
    );
  }

  return matchPath({ path, end: true }, currentPathname) !== null;
}

function ConsoleRobotAvatar() {
  return (
    <div
      aria-hidden="true"
      className="relative flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full border border-indigo-100 bg-[radial-gradient(circle_at_30%_30%,#f7ebff_0%,#e6ebff_52%,#d8e2ff_100%)] text-indigo-600"
    >
      <div className="absolute left-[4px] top-[5px] h-[3px] w-[4px] rounded-full bg-[#d18cff] opacity-80" />
      <div className="absolute right-[4px] top-[5px] h-[3px] w-[4px] rounded-full bg-[#b9c9ff] opacity-80" />
      <div className="relative flex h-[16px] w-[18px] items-center justify-center rounded-[5px] bg-[linear-gradient(180deg,#942dd3_0%,#7b1fc5_100%)] shadow-[0_2px_6px_rgba(123,31,197,0.24)]">
        <div className="absolute -top-[3px] left-1/2 h-[4px] w-[8px] -translate-x-1/2 rounded-full border border-[#9729d2] bg-white/70" />
        <div className="absolute left-[3px] top-[6px] h-[2px] w-[3px] rounded-full bg-white" />
        <div className="absolute right-[3px] top-[6px] h-[2px] w-[3px] rounded-full bg-white" />
        <div className="absolute top-[7px] h-[1.5px] w-[4px] rounded-full bg-white/80" />
        <div className="absolute bottom-[4px] h-[1.5px] w-[9px] rounded-full bg-[#2b1446]" />
        <div className="absolute -left-[2px] top-[5px] h-[5px] w-[1.5px] rounded-full bg-[#942dd3]" />
        <div className="absolute -right-[2px] top-[5px] h-[5px] w-[1.5px] rounded-full bg-[#942dd3]" />
      </div>
    </div>
  );
}

export function ConsoleSidebar({
  menus,
  username,
  roleLabel,
  onLogout,
}: {
  menus: MenuNode[];
  username?: string;
  roleLabel?: string;
  onLogout?: () => Promise<void>;
}) {
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const navItems = useMemo(() => buildPrototypeNav(menus), [menus]);
  const permissionsActive =
    matchPath({ path: "/system/users", end: true }, location.pathname) !== null ||
    matchPath({ path: "/system/roles", end: true }, location.pathname) !== null;
  const [permissionsExpanded, setPermissionsExpanded] = useState(permissionsActive);

  useEffect(() => {
    if (permissionsActive) {
      setPermissionsExpanded(true);
    }
  }, [permissionsActive]);

  async function handleLogout() {
    if (onLogout === undefined) {
      return;
    }

    setSubmitting(true);
    try {
      await onLogout();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <aside className="relative hidden h-screen w-64 shrink-0 select-none flex-col justify-between border-r border-slate-200/80 bg-slate-50 text-slate-600 lg:flex">
      <div className="flex-1 overflow-y-auto">
        <div className="border-b border-slate-200/60 p-6">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded-[4px] border border-indigo-200/40 bg-indigo-50 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-indigo-700">
              AI Code Review
            </span>
          </div>

          <div className="space-y-1">
            <h1 className="flex items-center gap-1.5 text-lg font-bold tracking-tight text-slate-800">
              <span>审查控制台</span>
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </h1>
            <p className="text-[11px] leading-relaxed text-slate-400">
              智能代码审计与研发效能引擎
            </p>
          </div>
        </div>

        <nav className="space-y-1 p-3" aria-label="控制台导航">
          {navItems.map((item) => {
            if (item.id === "permissions" && item.children) {
              return (
                <div key={item.id} className="space-y-1">
                  <button
                    type="button"
                    onClick={() => setPermissionsExpanded((current) => !current)}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all ${
                      permissionsActive
                        ? "bg-indigo-50/40 font-semibold text-indigo-700"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <item.icon
                        className={`h-4 w-4 ${
                          permissionsActive ? "text-indigo-600" : "text-slate-400"
                        }`}
                      />
                      <span>权限管理</span>
                    </div>
                    {permissionsExpanded ? (
                      <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
                    )}
                  </button>

                  {permissionsExpanded ? (
                    <div className="ml-5 space-y-1.5 overflow-hidden border-l border-slate-200/60 pl-4">
                      {item.children.map((child) => {
                        const active = isPathActive(location.pathname, child.path);
                        return (
                          <Link
                            key={child.id}
                            to={child.path}
                            className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-xs font-medium transition-all ${
                              active
                                ? "bg-indigo-50/80 font-bold text-indigo-700"
                                : "text-slate-500 hover:bg-slate-100/70 hover:text-slate-800"
                            }`}
                          >
                            <child.icon
                              className={`h-3.5 w-3.5 ${
                                active ? "text-indigo-600" : "text-slate-400"
                              }`}
                            />
                            <span>{child.text}</span>
                          </Link>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              );
            }

            if (!item.path) {
              return null;
            }

            const active = isPathActive(location.pathname, item.path);
            const Icon = item.icon;

            return (
              <Link
                key={item.id}
                to={item.path}
                className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all ${
                  active
                    ? "rounded-l-none border-l-2 border-indigo-600/80 bg-indigo-50 pl-2.5 font-bold text-indigo-600"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`h-4 w-4 transition-colors ${
                      active ? "text-indigo-600" : "text-slate-400"
                    }`}
                  />
                  <span>{item.text}</span>
                </div>

                {item.badge ? (
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-[9.5px] font-bold ${
                      item.badge === "NEW"
                        ? "bg-indigo-600 text-white shadow-sm"
                        : active
                          ? "bg-indigo-100 text-indigo-700"
                          : "bg-slate-200/60 text-slate-600"
                    }`}
                  >
                    {item.badge}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>
      </div>

      {username && roleLabel && onLogout ? (
        <div className="shrink-0 space-y-3 border-t border-slate-200/60 bg-slate-50 p-4">
          <div className="flex items-center gap-2.5 rounded-xl border border-slate-200/60 bg-white p-2 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
            <ConsoleRobotAvatar />
            <div className="min-w-0 grow">
              <div className="truncate font-mono text-xs font-bold text-slate-700" title={username}>
                {username}
              </div>
              <div className="truncate text-[10px] font-medium text-slate-400">{roleLabel}</div>
            </div>
          </div>

          <div className="flex items-center justify-between gap-1 px-1">
            <span className="font-mono text-[9px] font-semibold tracking-wider text-slate-400">
              CONSOLE v2.1.0
            </span>
            <button
              type="button"
              onClick={() => void handleLogout()}
              disabled={submitting}
              className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-600 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-all hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
              title="退出登录"
            >
              <LogOut className="h-3 w-3" />
              <span>{submitting ? "退出中..." : "退出"}</span>
            </button>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
