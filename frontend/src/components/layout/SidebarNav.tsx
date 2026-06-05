import type { MenuNode } from "../../lib/api/types";
import { ConsoleSidebar } from "../console/ConsoleSidebar";

/**
 * SidebarNav 保留兼容导出，内部已切换到高保真 console 侧边栏实现。
 */
export function SidebarNav({
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
  return (
    <ConsoleSidebar
      menus={menus}
      username={username}
      roleLabel={roleLabel}
      onLogout={onLogout}
    />
  );
}
