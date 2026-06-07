/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { LogOut, User, Menu, RefreshCw, Calendar, Sparkles } from 'lucide-react';
import { UserSession, TabId } from '../types';

interface HeaderProps {
  session: UserSession;
  activeTab: TabId;
  onLogout: () => void;
  onRefreshData?: () => void;
}

export default function Header({ session, activeTab, onLogout, onRefreshData }: HeaderProps) {
  // Title map based on RBAC Active Tabs
  const getTabTitle = (tab: TabId) => {
    switch (tab) {
      case 'dashboard':
        return '欢迎回来';
      case 'projects':
        return '项目管理';
      case 'templates':
        return '项目模板管理';
      case 'models':
        return '模型管理';
      case 'robots':
        return '通知机器人配置';
      case 'records':
        return '智能审查记录';
      case 'members':
        return '团队成员分析';
      case 'permissions':
        return '系统权限管理 (RBAC)';
      case 'users':
        return '系统用户中心';
      case 'roles':
        return '智能角色矩阵';
      case 'logs':
        return '系统审计日志';
      case 'chat':
        return '仓库对话助手';
      default:
        return 'AI Code Review';
    }
  };

  return (
    <header className="bg-white/60 backdrop-blur-xs border-b border-slate-200/50 px-8 py-3 flex items-center justify-between">
      {/* Left Breadcrumbs Path */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 font-mono">
          管理台
        </span>
        <span className="text-slate-300 font-mono">/</span>
        <span className="text-xs text-indigo-650 font-bold bg-indigo-50/50 px-2 py-0.5 rounded-xs border border-indigo-100">
          {getTabTitle(activeTab)}
        </span>
      </div>

      {/* Right Controls Area with Compact Refresh Action */}
      <div className="flex items-center gap-3">
        {onRefreshData && (
          <button
            onClick={onRefreshData}
            title="刷新系统数据"
            className="flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-slate-50 text-slate-500 hover:text-indigo-650 border border-slate-200 rounded-lg text-xs font-semibold shadow-3xs cursor-pointer transition-colors active:scale-95"
          >
            <RefreshCw className="w-3 h-3" />
            <span className="text-[10px] sm:inline hidden">同步状态</span>
          </button>
        )}
      </div>
    </header>
  );
}
