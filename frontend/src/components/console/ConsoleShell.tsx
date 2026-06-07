import { Outlet } from "react-router-dom";
import type { ReactNode } from "react";

import type { MenuNode } from "../../lib/api/types";
import { ConsoleSidebar } from "./ConsoleSidebar";
import { ConsoleTopbar } from "./ConsoleTopbar";

export function ConsoleShell({
  menus,
  username,
  nickname,
  roleLabel,
  mustChangePassword,
  onLogout,
  children,
}: {
  menus: MenuNode[];
  username: string;
  nickname: string | null;
  roleLabel: string;
  mustChangePassword: boolean;
  onLogout: () => Promise<void>;
  children?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-[#f1f5f9] text-slate-800">
      <ConsoleSidebar menus={menus} username={username} roleLabel={roleLabel} onLogout={onLogout} />
      <div className="flex min-h-screen flex-1 flex-col overflow-y-auto">
        <ConsoleTopbar
          username={username}
          nickname={nickname}
          mustChangePassword={mustChangePassword}
          onLogout={onLogout}
          onRefresh={() => Promise.resolve()}
        />
        <main className="flex-1 pb-16">
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}
