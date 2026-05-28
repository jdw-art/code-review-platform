import {
  Bot,
  Copy,
  Cpu,
  FileSearch,
  FolderKanban,
  FolderOpen,
  LayoutDashboard,
  PanelLeft,
  ScrollText,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

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

/**
 * SidebarNav 根据 RBAC 菜单树递归渲染导航，后续页面只需要关注路由本身。
 */
export function SidebarNav({ menus }: { menus: MenuNode[] }) {
  const sortedMenus = sortMenus(menus);

  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-slate-950 px-5 py-6 text-slate-100 lg:block">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
        <p className="text-xs uppercase tracking-[0.3em] text-cyan-200/80">
          AI Code Review
        </p>
        <p className="mt-3 text-2xl font-semibold">管理后台</p>
        <p className="mt-2 text-sm text-slate-300">
          认证、菜单与核心后台能力先落起来。
        </p>
      </div>
      <nav className="mt-8 space-y-2" aria-label="后台导航">
        {sortedMenus.map((menu) => (
          <SidebarItem key={menu.id} menu={menu} depth={0} />
        ))}
      </nav>
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
  const Icon = resolveIcon(menu.icon);
  const children = sortMenus(menu.children);

  return (
    <div className="space-y-2">
      <NavLink
        to={menu.path}
        className={({ isActive }) =>
          [
            "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition",
            "border border-transparent",
            isActive
              ? "border-cyan-300/20 bg-cyan-300/10 text-white shadow-[0_0_0_1px_rgba(34,211,238,0.08)]"
              : "text-slate-300 hover:border-white/10 hover:bg-white/5 hover:text-white",
          ].join(" ")
        }
        style={{ marginLeft: depth === 0 ? 0 : depth * 12 }}
      >
        <Icon className="h-4 w-4 shrink-0" />
        <span className="truncate">{menu.name}</span>
      </NavLink>
      {children.length > 0 ? (
        <div className="space-y-2">
          {children.map((child) => (
            <SidebarItem key={child.id} menu={child} depth={depth + 1} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
