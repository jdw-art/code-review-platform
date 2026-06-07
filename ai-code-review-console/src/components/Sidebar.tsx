/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  LayoutDashboard,
  FolderCode,
  FileJson,
  Cpu,
  Bot,
  BookmarkCheck,
  Users,
  KeyRound,
  UserCheck,
  ShieldAlert,
  ScrollText,
  BadgeCheck,
  ChevronDown,
  ChevronRight,
  LogOut,
  User,
} from 'lucide-react';
import { TabId, UserSession } from '../types';

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  session: UserSession;
  onLogout: () => void;
}

export default function Sidebar({ activeTab, onTabChange, session, onLogout }: SidebarProps) {
  // Navigation specs mapped directly from design requirements
  const menuGroup = [
    { id: 'dashboard', text: '仪表盘', icon: LayoutDashboard },
    { id: 'projects', text: '项目管理', icon: FolderCode, badge: '6' },
    { id: 'templates', text: '项目模板管理', icon: FileJson },
    { id: 'models', text: '模型管理', icon: Cpu, badge: 'NEW' },
    { id: 'robots', text: '通知机器人', icon: Bot },
    { id: 'records', text: '审查记录', icon: BookmarkCheck, badge: '30' },
    { id: 'members', text: '成员分析', icon: Users },
  ];

  const subItems = [
    { id: 'users', text: '用户管理', icon: UserCheck },
    { id: 'roles', text: '角色管理', icon: ShieldAlert },
  ];

  // Accordion active expanded state
  const [permissionsExpanded, setPermissionsExpanded] = useState(() => {
    return activeTab === 'users' || activeTab === 'roles';
  });

  useEffect(() => {
    if (activeTab === 'users' || activeTab === 'roles') {
      setPermissionsExpanded(true);
    }
  }, [activeTab]);

  const isPermissionsGroupActive = activeTab === 'users' || activeTab === 'roles';

  return (
    <div className="w-64 bg-slate-50 text-slate-600 shrink-0 h-screen flex flex-col justify-between border-r border-slate-200/80 relative select-none">
      {/* Scrollable menu block */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {/* Top Header Card Block */}
        <div className="p-6 border-b border-slate-200/60">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[9px] uppercase tracking-widest text-indigo-650 font-bold px-1.5 py-0.5 bg-indigo-50 rounded-xs border border-indigo-200/40">
              AI Code Review
            </span>
          </div>

          <div className="space-y-1">
            <h2 className="text-lg font-bold text-slate-800 tracking-tight flex items-center gap-1.5">
              <span>审查控制台</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse" />
            </h2>
            <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
              智能代码审计与研发效能引擎
            </p>
          </div>
        </div>

        {/* Sidebar Nav links */}
        <nav className="p-3 space-y-1">
          {menuGroup.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id || (item.id === 'projects' && activeTab === 'chat');

            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id as TabId)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-600 border-l-2 border-indigo-600/80 font-bold pl-2.5 rounded-l-none'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                     className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-indigo-600' : 'text-slate-400'
                    }`}
                  />
                  <span>{item.text}</span>
                </div>

                {/* Subtitle count badge */}
                {item.badge && (
                  <span
                    className={`text-[9.5px] px-1.5 py-0.5 font-bold rounded-full ${
                      item.badge === 'NEW'
                        ? 'bg-indigo-600 text-white shadow-2xs'
                        : isActive
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'bg-slate-200/60 text-slate-600'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}

          {/* Integrated Collapsible Permission Management Menu */}
          <div className="space-y-1">
            <button
              onClick={() => setPermissionsExpanded(!permissionsExpanded)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                isPermissionsGroupActive
                  ? 'bg-indigo-50/40 text-indigo-650 font-semibold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <KeyRound
                  className={`w-4 h-4 transition-colors ${
                    isPermissionsGroupActive ? 'text-indigo-600' : 'text-slate-400'
                  }`}
                />
                <span>权限管理</span>
              </div>
              <div>
                {permissionsExpanded ? (
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                )}
              </div>
            </button>

            {/* Nested Secondary Menus */}
            <AnimatePresence initial={false}>
              {permissionsExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.18 }}
                  className="pl-4 space-y-1.5 overflow-hidden border-l border-slate-200/60 ml-5"
                >
                  {subItems.map((sub) => {
                    const SubIcon = sub.icon;
                    const isSubActive = activeTab === sub.id;
                    return (
                      <button
                        key={sub.id}
                        onClick={() => onTabChange(sub.id as TabId)}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                          isSubActive
                            ? 'bg-indigo-55/80 text-indigo-750 font-bold'
                            : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100/70'
                        }`}
                      >
                        <SubIcon
                          className={`w-3.5 h-3.5 ${
                            isSubActive ? 'text-indigo-600 font-bold' : 'text-slate-400'
                          }`}
                        />
                        <span>{sub.text}</span>
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* System Audit Log item of menu */}
          <button
            onClick={() => onTabChange('logs')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all ${
              activeTab === 'logs'
                ? 'bg-indigo-50 text-indigo-600 border-l-2 border-indigo-600/80 font-bold pl-2.5 rounded-l-none'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <div className="flex items-center gap-3">
              <ScrollText
                className={`w-4 h-4 transition-colors ${
                  activeTab === 'logs' ? 'text-indigo-600' : 'text-slate-400'
                }`}
              />
              <span>系统日志</span>
            </div>
          </button>
        </nav>
      </div>

      {/* Sidebar Footer User & System info panel (Fixed at Bottom-Left) */}
      <div className="p-4 border-t border-slate-200/60 space-y-3 bg-slate-50 shrink-0">
        {/* User Profile Info Card */}
        <div className="flex items-center gap-2.5 p-2 bg-white rounded-xl border border-slate-200/60 shadow-2xs">
          <div className="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-xs uppercase overflow-hidden shrink-0">
            {session.avatarUrl ? (
              <img src={session.avatarUrl} alt="Avatar" referrerPolicy="no-referrer" className="w-full h-full object-cover" />
            ) : (
              <User className="w-4 h-4 text-indigo-600" />
            )}
          </div>
          <div className="grow min-w-0">
            <div className="text-xs font-bold text-slate-700 font-mono truncate" title={session.username}>
              {session.username || 'jdw-art'}
            </div>
            <div className="text-[10px] text-slate-400 font-medium truncate">
              {session.role || '超级管理员'}
            </div>
          </div>
        </div>

        {/* Console info & Logout buttons Row */}
        <div className="flex items-center justify-between gap-1 px-1">
          <span className="text-[9px] text-slate-400 font-mono tracking-wider font-semibold">
            CONSOLE v2.1.0
          </span>
          <button
            onClick={onLogout}
            className="flex items-center gap-1 px-2 py-1 bg-white hover:bg-rose-50 border border-slate-200 hover:border-rose-200 text-slate-600 hover:text-rose-700 rounded-lg text-[10px] font-semibold transition-all cursor-pointer shadow-3xs active:scale-[0.97]"
            title="退出登录"
          >
            <LogOut className="w-3 h-3" />
            <span>退出</span>
          </button>
        </div>
      </div>
    </div>
  );
}
