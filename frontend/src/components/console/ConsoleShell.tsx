import { Outlet } from "react-router-dom";
import type { ReactNode } from "react";

import type { MenuNode } from "../../lib/api/types";
import { ConsoleSidebar } from "./ConsoleSidebar";
import { ConsoleTopbar } from "./ConsoleTopbar";

export function ConsoleShell({
  menus,
  username,
  roleLabel,
  mustChangePassword,
  onLogout,
  children,
}: {
  menus: MenuNode[];
  username: string;
  roleLabel: string;
  mustChangePassword: boolean;
  onLogout: () => Promise<void>;
  children?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-[#f1f5f9] text-slate-800">
      <ConsoleSidebar menus={menus} username={username} roleLabel={roleLabel} onLogout={onLogout} />
      <div className="flex min-h-screen flex-1 flex-col overflow-y-auto">
        <ConsoleTopbar mustChangePassword={mustChangePassword} onLogout={onLogout} />
        <main className="flex-1 px-4 pb-10 pt-6 sm:px-6 lg:px-8">
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}
