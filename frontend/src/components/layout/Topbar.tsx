import { ConsoleTopbar } from "../console/ConsoleTopbar";

/**
 * Topbar 保留兼容导出，内部已切换到高保真 console 顶栏实现。
 */
export function Topbar({
  mustChangePassword = false,
  onLogout,
}: {
  username?: string;
  nickname?: string | null;
  mustChangePassword?: boolean;
  onLogout: () => Promise<void>;
}) {
  return <ConsoleTopbar mustChangePassword={mustChangePassword} onLogout={onLogout} />;
}
