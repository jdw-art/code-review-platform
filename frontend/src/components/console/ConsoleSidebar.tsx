import {
  Bot,
  ChevronRight,
  Copy,
  Cpu,
  FileSearch,
  FolderKanban,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  PanelLeft,
  ScrollText,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import { NavLink, matchPath, useLocation } from "react-router-dom";
import { useState } from "react";

import type { MenuNode } from "../../lib/api/types";

const iconMap: Record<string, LucideIcon> = {
  bot: Bot,
  copy: Copy,
  cpu: Cpu,
  "file-search": FileSearch,
  "folder-kanban": FolderKanban,
  "folder-open": FolderOpen,
  "layout-dashboard": LayoutDashboard,
  "scroll-text": ScrollText,
  "shield-check": ShieldCheck,
  users: Users,
};

function resolveIcon(iconName: string | null) {
  if (iconName === null) {
    return PanelLeft;
  }
  return iconMap[iconName] ?? PanelLeft;
}

function sortMenus(menus: MenuNode[]) {
  return [...menus].filter((menu) => menu.visible).sort((left, right) => left.sort - right.sort);
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
  const [submitting, setSubmitting] = useState(false);
  const sortedMenus = sortMenus(menus);

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
    <aside className="hidden h-screen w-72 shrink-0 flex-col justify-between border-r border-slate-200/80 bg-slate-50 lg:flex">
      <div className="overflow-y-auto">
        <div className="border-b border-slate-200/70 px-6 py-6">
          <span className="inline-flex items-center rounded-md border border-indigo-200/80 bg-indigo-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.28em] text-indigo-700">
            AI Code Review
          </span>
          <div className="mt-4 space-y-1">
            <h1 className="flex items-center gap-2 text-lg font-bold tracking-tight text-slate-800">
              <span>智能控制台</span>
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
            </h1>
            <p className="text-[11px] text-slate-400">智能代码审计与研发效能引擎</p>
          </div>
        </div>

        <nav className="space-y-1 p-3" aria-label="控制台导航">
          {sortedMenus.map((menu) => (
            <SidebarItem key={menu.id} menu={menu} depth={0} />
          ))}
        </nav>
      </div>

      {username && roleLabel && onLogout ? (
        <div className="space-y-3 border-t border-slate-200/70 bg-slate-50 px-4 py-4">
          <div className="rounded-xl border border-slate-200/70 bg-white px-3 py-2.5">
            <p className="truncate text-xs font-bold uppercase text-slate-700">{username}</p>
            <p className="mt-1 truncate text-[11px] text-slate-400">{roleLabel}</p>
          </div>
          <div className="flex items-center justify-between gap-2 px-1">
            <span className="text-[10px] font-semibold tracking-[0.24em] text-slate-400">
              CONSOLE
            </span>
            <button
              type="button"
              onClick={handleLogout}
              disabled={submitting}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
              title="退出登录"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>{submitting ? "退出中..." : "退出"}</span>
            </button>
          </div>
        </div>
      ) : null}
    </aside>
  );
}

function SidebarItem({
  menu,
  depth,
}: {
  menu: MenuNode;
  depth: number;
}) {
  const location = useLocation();
  const Icon = resolveIcon(menu.icon);
  const children = sortMenus(menu.children);
  const isCurrentRoute = matchPath({ path: menu.path, end: true }, location.pathname) !== null;
  const isChildRouteActive = children.some(
    (child) =>
      matchPath({ path: child.path, end: false }, location.pathname) !== null
  );
  const isActive = isCurrentRoute || isChildRouteActive;

  return (
    <div className="space-y-1">
      <NavLink
        to={menu.path}
        end={children.length === 0}
        className={() =>
          [
            "flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all",
            isActive
              ? "bg-indigo-50 text-indigo-700"
              : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
          ].join(" ")
        }
        style={{ marginLeft: depth === 0 ? 0 : depth * 14 }}
      >
        <span className="flex min-w-0 items-center gap-3">
          <Icon className="h-4 w-4 shrink-0" />
          <span className="truncate">{menu.name}</span>
        </span>
        {children.length > 0 ? <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-400" /> : null}
      </NavLink>
      {children.length > 0 ? (
        <div className="space-y-1">
          {children.map((child) => (
            <SidebarItem key={child.id} menu={child} depth={depth + 1} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
