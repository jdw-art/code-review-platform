/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  Bot,
  Slack,
  MessageSquare,
  Sparkles,
  GitPullRequest,
  GitBranch,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  Send,
  Users,
  Award,
  BarChart,
  UserCheck,
  ShieldCheck,
  KeyRound,
  Eye,
  Settings,
  Mail,
  Smartphone,
  Check,
  AlertCircle,
  Hash,
  Activity,
  Layers,
  Terminal,
  X,
  PlusCircle,
  Trash2,
  Lock,
  ChevronLeft,
  ChevronRight,
  Pencil,
  EyeOff,
} from 'lucide-react';
import * as Lucide from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ReviewRecord, ProjectItem } from '../types';

/* ==========================================================
 * 1. NOTIFY ROBOTS CONFIGURATION (通知机器人 - notification_bots)
 * ========================================================== */
export function RobotsView({ onAddLog }: { onAddLog?: (action: string, text: string) => void }) {
  // Configured robot type definition schema
  interface BotConfig {
    id: string;
    name: string;
    bot_type: 'feishu' | 'slack' | 'dingtalk' | 'custom' | string;
    webhook_url: string;
    secret_masked: string;
    mention_strategy: string;
    is_active: boolean;
    last_test_status: 'success' | 'failed' | string;
    last_test_message: string;
  }

  // Load from localStorage or defaults
  const [bots, setBots] = useState<BotConfig[]>(() => {
    try {
      const saved = localStorage.getItem('review_notification_bots');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to restore notification_bots from storage:', e);
    }
    return [
      {
        id: 'bot_id_feishu',
        name: '飞书交互卡片机器人',
        bot_type: 'feishu',
        webhook_url: 'https://open.feishu.cn/open-apis/bot/v2/hook/f8bca1-jdw9921',
        secret_masked: 'tb_secret_feishu_key_secure',
        mention_strategy: '@user_id',
        is_active: true,
        last_test_status: 'success',
        last_test_message: 'Interactive card delivery finished successfully.',
      },
      {
        id: 'bot_id_slack',
        name: 'Slack Webhook Hub',
        bot_type: 'slack',
        webhook_url: 'https://hooks.slack.com/services/T0000/B0000/JDW8812',
        secret_masked: 'slack_secret_token_oauth_xyz',
        mention_strategy: 'none',
        is_active: false,
        last_test_status: 'success',
        last_test_message: 'JSON response approved.',
      },
      {
        id: 'bot_id_dingtalk',
        name: '钉钉诊断群助手',
        bot_type: 'dingtalk',
        webhook_url: 'https://oapi.dingtalk.com/robot/send?access_token=dd88127391',
        secret_masked: 'ding_secret_timestamp_digest_val',
        mention_strategy: '@all',
        is_active: false,
        last_test_status: 'failed',
        last_test_message: 'DNS lookup timeout error during secure sync.',
      },
    ];
  });

  // Sync back to local storage
  useEffect(() => {
    localStorage.setItem('review_notification_bots', JSON.stringify(bots));
  }, [bots]);

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(6);

  // Form management
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingBot, setEditingBot] = useState<BotConfig | null>(null);

  // Form Field States
  const [formName, setFormName] = useState('');
  const [formType, setFormType] = useState('feishu');
  const [formUrl, setFormUrl] = useState('');
  const [formSecret, setFormSecret] = useState('');
  const [formMention, setFormMention] = useState('@all');
  const [formActive, setFormActive] = useState(true);

  // Unmasked secrets toggle mapping
  const [unmaskedSecrets, setUnmaskedSecrets] = useState<Record<string, boolean>>({});

  // Toast System
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' | null }>({
    message: '',
    type: null,
  });

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast((prev) => (prev.message === message ? { message: '', type: null } : prev));
    }, 3000);
  };

  // Reset states
  const resetForm = () => {
    setFormName('');
    setFormType('feishu');
    setFormUrl('');
    setFormSecret('');
    setFormMention('@all');
    setFormActive(true);
  };

  const handleOpenAdd = () => {
    resetForm();
    setIsAddOpen(true);
  };

  const handleOpenEdit = (bot: BotConfig) => {
    setEditingBot(bot);
    setFormName(bot.name);
    setFormType(bot.bot_type);
    setFormUrl(bot.webhook_url);
    setFormSecret(bot.secret_masked);
    setFormMention(bot.mention_strategy);
    setFormActive(bot.is_active);
  };

  // Save Add
  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formUrl.trim()) {
      showToast('请输入名称和 Webhook 链接', 'error');
      return;
    }

    const newBot: BotConfig = {
      id: `bot_id_${Date.now()}`,
      name: formName,
      bot_type: formType,
      webhook_url: formUrl,
      secret_masked: formSecret || '•••••••••',
      mention_strategy: formMention,
      is_active: formActive,
      last_test_status: 'success',
      last_test_message: 'Webhook configuration initialized.',
    };

    setBots((prev) => [newBot, ...prev]);
    setIsAddOpen(false);
    resetForm();
    showToast(`成功新增通道：${newBot.name}`);
    
    if (onAddLog) {
      onAddLog('ROBOT_CREATED', `成功添加通知机器人通道: ${newBot.name} (类型: ${newBot.bot_type})`);
    }
  };

  // Save Edit
  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingBot) return;
    if (!formName.trim() || !formUrl.trim()) {
      showToast('请输入名称与 Webhook 链接', 'error');
      return;
    }

    setBots((prev) =>
      prev.map((bot) =>
        bot.id === editingBot.id
          ? {
              ...bot,
              name: formName,
              bot_type: formType,
              webhook_url: formUrl,
              secret_masked: formSecret,
              mention_strategy: formMention,
              is_active: formActive,
            }
          : bot
      )
    );
    
    setEditingBot(null);
    showToast(`成功更新通道：${formName}`);
    
    if (onAddLog) {
      onAddLog('ROBOT_UPDATED', `修改了通知机器人通道: ${formName} 参数`);
    }
  };

  // Delete
  const handleDeleteBot = (id: string, name: string) => {
    if (window.confirm(`确定要删除通知机器人「${name}」吗？删除后将无法向此通道推送。`)) {
      setBots((prev) => prev.filter((bot) => bot.id !== id));
      showToast(`已删除通道：${name}`, 'info');
      if (onAddLog) {
        onAddLog('ROBOT_DELETED', `已删除通知机器人通道: ${name} (ID: ${id})`);
      }
    }
  };

  // Toggle active state
  const toggleBot = (id: string) => {
    setBots((prev) =>
      prev.map((bot) => {
        if (bot.id === id) {
          const nextState = !bot.is_active;
          showToast(`${bot.name} ${nextState ? '已启用监控' : '已暂停推送'}`);
          if (onAddLog) {
            onAddLog(
              'ROBOT_STATUS_TOGGLE',
              `通知机器人: ${bot.name} 的启用状态 (is_active) 切换为: ${nextState ? '启用' : '禁用'}`
            );
          }
          return { ...bot, is_active: nextState };
        }
        return bot;
      })
    );
  };

  // Simulate Testing with inline message rather than aggressive alert
  const handleTestBot = (id: string, name: string, botType: string) => {
    // Randomize status for flavor
    const ran = Math.random() > 0.15;
    const nextStatus = ran ? 'success' : 'failed';
    const nextMsg = ran 
      ? 'Interactive diagnostic card delivered successfully. HTTP 200 OK.' 
      : 'Target server returned rejection. Webhook handshake token mismatch.';

    setBots((prev) =>
      prev.map((bot) =>
        bot.id === id
          ? {
              ...bot,
              last_test_status: nextStatus,
              last_test_message: nextMsg,
            }
          : bot
      )
    );

    if (nextStatus === 'success') {
      showToast(`已成功向「${name}」发送诊断测试 Ping 卡片！`, 'success');
    } else {
      showToast(`向「${name}」发送测试卡片失败，请检查密钥或网络！`, 'error');
    }

    if (onAddLog) {
      onAddLog('PING_ROBOT', `向机器人通道 [${botType}] ${name} 派发生命值存活 Ping，状态: ${nextStatus.toUpperCase()}`);
    }
  };

  const copyUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    showToast('链接复制成功！', 'info');
  };

  // Compute paginated subset
  const totalItems = bots.length;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;
  const indexOfLastItem = currentPage * pageSize;
  const indexOfFirstItem = Math.max(0, indexOfLastItem - pageSize);
  const currentBots = bots.slice(indexOfFirstItem, indexOfLastItem);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage]);

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto relative">
      {/* Toast notifier banner overlay */}
      <AnimatePresence>
        {toast.message && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-lg border text-xs font-sans font-semibold flex items-center gap-2 ${
              toast.type === 'error'
                ? 'bg-red-50 text-red-700 border-red-200'
                : toast.type === 'info'
                ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                : 'bg-emerald-50 text-emerald-700 border-emerald-200'
            }`}
          >
            {toast.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
            ) : toast.type === 'info' ? (
              <Sparkles className="w-4 h-4 text-indigo-500 shrink-0" />
            ) : (
              <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
            )}
            <span>{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="bg-white py-4 px-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-0.5">
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Bot className="w-4.5 h-4.5 text-indigo-500 shrink-0 animate-pulse" />
            <span>通知机器人通道矩阵</span>
          </h2>
          <p className="text-[11px] text-slate-500">
            定制配置各种 IM 即时通讯工具 Webhook 机器人，发生严重研发缺陷或代码健康风险时即时派发卡片。
          </p>
        </div>

        <button
          onClick={handleOpenAdd}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm hover:shadow-md cursor-pointer flex items-center gap-1.5 shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          <span>配置新机器人通道</span>
        </button>
      </div>

      {bots.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 space-y-3">
          <Bot className="w-12 h-12 text-slate-300 mx-auto opacity-60" />
          <p className="text-xs">暂无配置的通知通道机器人组件，点击右上方按钮开始新增</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {currentBots.map((bot) => {
              const isUnmasked = unmaskedSecrets[bot.id] ?? false;
              return (
                <div
                  key={bot.id}
                  className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col justify-between space-y-6 hover:shadow-md hover:border-slate-300 transition-all duration-300 relative group"
                >
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <div className="p-2 rounded-xl bg-slate-50 text-slate-500">
                          {bot.bot_type === 'feishu' ? (
                            <MessageSquare className="w-5 h-5 text-emerald-500" />
                          ) : bot.bot_type === 'slack' ? (
                            <Slack className="w-5 h-5 text-purple-500" />
                          ) : bot.bot_type === 'dingtalk' ? (
                            <Bot className="w-5 h-5 text-blue-500" />
                          ) : (
                            <Settings className="w-5 h-5 text-indigo-500" />
                          )}
                        </div>
                        <span className="text-[10px] uppercase font-mono font-bold bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          {bot.bot_type}
                        </span>
                      </div>

                      <button
                        onClick={() => toggleBot(bot.id)}
                        className={`px-3 py-1 text-xs font-bold rounded-full cursor-pointer transition-all ${
                          bot.is_active ? 'bg-emerald-500 text-white shadow-xs' : 'bg-slate-100 text-slate-400'
                        }`}
                      >
                        {bot.is_active ? '已激活' : '已暂停'}
                      </button>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold text-slate-930 line-clamp-1">{bot.name}</h3>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleOpenEdit(bot)}
                            className="p-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-all cursor-pointer"
                            title="编辑"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteBot(bot.id, bot.name)}
                            className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-all cursor-pointer"
                            title="删除"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-400 font-mono">ID: {bot.id}</p>
                    </div>

                    {/* Webhook and Secret */}
                    <div className="space-y-2 pt-2 border-t border-slate-100">
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold text-slate-400 uppercase flex justify-between">
                          <span>Webhook 链接</span>
                          <button
                            onClick={() => copyUrl(bot.webhook_url)}
                            className="text-[9px] text-indigo-500 hover:underline hover:text-indigo-600 cursor-pointer"
                          >
                            点击复制
                          </button>
                        </label>
                        <input
                          type="text"
                          readOnly
                          value={bot.webhook_url}
                          className="w-full px-2 py-1 text-[11px] bg-slate-50 border border-slate-200 rounded-lg text-slate-600 font-mono focus:outline-hidden text-ellipsis overflow-hidden"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] uppercase font-bold text-slate-400 flex justify-between">
                          <span>通道共享签名密钥</span>
                          <button
                            onClick={() =>
                              setUnmaskedSecrets((prev) => ({ ...prev, [bot.id]: !isUnmasked }))
                            }
                            className="text-[9px] text-indigo-500 hover:underline hover:text-indigo-600 cursor-pointer"
                          >
                            {isUnmasked ? '隐藏' : '显示'}
                          </button>
                        </label>
                        <input
                          type={isUnmasked ? 'text' : 'password'}
                          readOnly
                          value={bot.secret_masked}
                          className="w-full px-2 py-1 text-[11px] bg-slate-50 border border-slate-200 rounded-lg font-mono text-slate-500 focus:outline-hidden"
                        />
                      </div>

                      <div className="flex justify-between text-xs pt-1">
                        <span className="text-slate-400">提及策略 <code>(mention_strategy)</code></span>
                        <span className="font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-705 text-[10px] uppercase">
                          {bot.mention_strategy}
                        </span>
                      </div>

                      <div className="flex flex-col text-xs space-y-0.5 border-t border-slate-50 pt-1.5">
                        <div className="flex justify-between">
                          <span className="text-slate-400">心跳诊断状态</span>
                          <span
                            className={`font-semibold text-[10px] ${
                              bot.last_test_status === 'success' ? 'text-emerald-600' : 'text-red-500'
                            }`}
                          >
                            {bot.last_test_status === 'success' ? '在线 (SUCCESS)' : '异常 (FAILED)'}
                          </span>
                        </div>
                        {bot.last_test_message && (
                          <p className="text-[9px] text-slate-400 font-mono bg-slate-50 border border-slate-100 rounded p-1 line-clamp-2">
                            {bot.last_test_message}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleTestBot(bot.id, bot.name, bot.bot_type)}
                    disabled={!bot.is_active}
                    className="w-full py-2 bg-slate-10/50 hover:bg-slate-50 disabled:opacity-45 text-slate-600 hover:text-slate-900 text-xs font-semibold rounded-xl border border-slate-150 cursor-pointer flex items-center justify-center gap-1.5 transition-colors disabled:cursor-not-allowed"
                  >
                    <Send className="w-3 h-3 shrink-0" />
                    <span>执行存活测试 Ping</span>
                  </button>
                </div>
              );
            })}
          </div>

          {/* Pagination bar with options for RobotsView! */}
          {totalItems > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between border border-slate-200 bg-white px-6 py-4 rounded-2xl text-xs gap-4 select-none shadow-3xs">
              <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
                <div>
                  显示 <span className="font-semibold text-slate-800">{indexOfFirstItem + 1}</span> 至{' '}
                  <span className="font-semibold text-slate-800">{Math.min(indexOfLastItem, totalItems)}</span> 个，
                  共 <span className="font-semibold text-slate-800">{totalItems}</span> 个机器人
                </div>
                <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                  <span>每页显示:</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="border border-slate-200 bg-slate-50 text-slate-800 rounded-md px-2 py-1 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                  >
                    <option value={3}>3 条</option>
                    <option value={6}>6 条</option>
                    <option value={12}>12 条</option>
                    <option value={24}>24 条</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="px-3 py-1.5 border border-slate-200 rounded-lg text-slate-600 bg-slate-50 hover:bg-slate-100 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed font-medium transition-colors flex items-center gap-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>上一页</span>
                </button>
                <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                  <span className="font-bold text-indigo-650">{currentPage}</span>
                  <span className="text-slate-300">/</span>
                  <span>{totalPages}</span>
                </div>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  className="px-3 py-1.5 border border-slate-200 rounded-lg text-slate-600 bg-slate-50 hover:bg-slate-100 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed font-medium transition-colors flex items-center gap-1"
                >
                  <span>下一页</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* MODAL: ADD ROBOT CHANNEL */}
      <AnimatePresence>
        {isAddOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xl max-w-lg w-full space-y-4"
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-indigo-500" />
                  <h3 className="font-bold text-slate-900 text-sm">配置新通知推送通道</h3>
                </div>
                <button
                  onClick={() => setIsAddOpen(false)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleAddSubmit} className="space-y-4 text-xs">
                <div className="space-y-1">
                  <label className="text-slate-500 font-semibold">机器人名称 (name)</label>
                  <input
                    type="text"
                    required
                    placeholder="例如：极客审查群助理"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-slate-500 font-semibold">通道协议类型 (bot_type)</label>
                    <select
                      value={formType}
                      onChange={(e) => setFormType(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                    >
                      <option value="feishu">飞书 (Feishu Webhook)</option>
                      <option value="slack">Slack Incoming Webhook</option>
                      <option value="dingtalk">钉钉群聊助手 (DingTalk)</option>
                      <option value="custom">通用 HTTP 自定义接口</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-slate-500 font-semibold">提及消息策略 (mention_strategy)</label>
                    <input
                      type="text"
                      placeholder="e.g. @user_id 或 @all"
                      value={formMention}
                      onChange={(e) => setFormMention(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-500 font-semibold">Webhook 推送接收地址 (webhook_url)</label>
                  <input
                    type="url"
                    required
                    placeholder="https://hooks.example.com/..."
                    value={formUrl}
                    onChange={(e) => setFormUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl font-mono focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30 text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-slate-500 font-semibold">预共享机密令牌 / 验证 Token</label>
                  <input
                    type="text"
                    placeholder="可选项，如飞书安全密钥或 Slack OAuth Token"
                    value={formSecret}
                    onChange={(e) => setFormSecret(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl font-mono focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                  />
                </div>

                <div className="flex items-center gap-2 py-1">
                  <input
                    type="checkbox"
                    id="add_active_check"
                    checked={formActive}
                    onChange={(e) => setFormActive(e.target.checked)}
                    className="rounded-sm border-slate-200 text-indigo-650 cursor-pointer focus:ring-indigo-500/30 w-4 h-4"
                  />
                  <label htmlFor="add_active_check" className="text-slate-600 font-medium cursor-pointer">
                    立即激活此通道并开始自动推送 (is_active)
                  </label>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsAddOpen(false)}
                    className="px-4 py-2 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-500 cursor-pointer"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold cursor-pointer transition-colors shadow-sm"
                  >
                    确认创建
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL: EDIT ROBOT CHANNEL */}
      <AnimatePresence>
        {editingBot && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xl max-w-lg w-full space-y-4"
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <Pencil className="w-4.5 h-4.5 text-indigo-500" />
                  <h3 className="font-bold text-slate-900 text-sm">编辑通道配置</h3>
                </div>
                <button
                  onClick={() => setEditingBot(null)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
                <div className="space-y-1">
                  <label className="text-slate-500 font-semibold">机器人名称</label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-slate-500 font-semibold">通道协议类型</label>
                    <select
                      value={formType}
                      onChange={(e) => setFormType(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                    >
                      <option value="feishu">飞书 (Feishu Webhook)</option>
                      <option value="slack">Slack Incoming Webhook</option>
                      <option value="dingtalk">钉钉群聊助手 (DingTalk)</option>
                      <option value="custom">通用 HTTP 自定义接口</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-slate-500 font-semibold">提及消息策略</label>
                    <input
                      type="text"
                      value={formMention}
                      onChange={(e) => setFormMention(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-500 font-semibold">Webhook 推送接收地址</label>
                  <input
                    type="url"
                    required
                    value={formUrl}
                    onChange={(e) => setFormUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl font-mono focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-slate-500 font-semibold">预共享密钥/机密校验口令</label>
                  <input
                    type="text"
                    value={formSecret}
                    onChange={(e) => setFormSecret(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 bg-slate-50 focus:bg-white rounded-xl font-mono focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                  />
                </div>

                <div className="flex items-center gap-2 py-1">
                  <input
                    type="checkbox"
                    id="edit_active_check"
                    checked={formActive}
                    onChange={(e) => setFormActive(e.target.checked)}
                    className="rounded-sm border-slate-200 text-indigo-650 cursor-pointer focus:ring-indigo-500/30 w-4 h-4"
                  />
                  <label htmlFor="edit_active_check" className="text-slate-600 font-medium cursor-pointer">
                    维持/激活此通道的正常服务状态 (is_active)
                  </label>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setEditingBot(null)}
                    className="px-4 py-2 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-500 cursor-pointer"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold cursor-pointer transition-colors shadow-sm"
                  >
                    更新配置
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ==========================================================
 * 2. REVIEW RECORDS FULL MASTER TABLE (审查记录中心 - review_records)
 * ========================================================== */
export function ReviewRecordsFullView({ records }: { records: ReviewRecord[] }) {
  const [search, setSearch] = useState('');
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, pageSize]);

  const filtered = records.filter((rec) => {
    const pName = rec.projectName || rec.project_name || '';
    const prTitleText = rec.prTitle || rec.title || '';
    const authorVal = rec.author || rec.committer || '';
    return (
      pName.toLowerCase().includes(search.toLowerCase()) ||
      prTitleText.toLowerCase().includes(search.toLowerCase()) ||
      authorVal.toLowerCase().includes(search.toLowerCase())
    );
  });

  const totalItems = filtered.length;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;
  const indexOfLastItem = currentPage * pageSize;
  const indexOfFirstItem = Math.max(0, indexOfLastItem - pageSize);
  const currentRecords = filtered.slice(indexOfFirstItem, indexOfLastItem);

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      {/* Header card with details */}
      <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200 shadow-3xs flex justify-between items-center">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
            <GitPullRequest className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>智能审查记录控制中心</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            双向溯源全部 PR 审查评分及 diff 修改记录。数据完全对齐 <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-650 font-mono">review_records</code> 数据表。
          </p>
        </div>
      </div>

      {/* Global Filter Search Input */}
      <div className="relative max-w-md w-full">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="按照项目名称、提交标题、作者进行全局过滤..."
          className="w-full px-4 py-2 text-xs bg-white text-slate-800 border border-slate-200 rounded-xl focus:outline-hidden"
        />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="divide-y divide-slate-100">
          {currentRecords.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-xs">
              暂无匹配的审查记录数据
            </div>
          ) : (
            currentRecords.map((record) => {
              const isExcellent = record.score >= 90;
              const isPass = record.score >= 70 && record.score < 90;
              const isWarning = record.score >= 60 && record.score < 70;
              const committerName = record.author || record.committer;
              const scoreStatus = isExcellent ? 'excellent' : isPass ? 'pass' : isWarning ? 'warning' : 'fail';

              return (
                <div key={record.id} className="py-4.5 px-6 flex flex-col md:flex-row justify-between md:items-center gap-5 hover:bg-slate-50/20 transition-colors">
                  <div className="space-y-2.5 max-w-4xl grow min-w-0">
                    {/* Title and tags info */}
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                        <span className="font-bold text-slate-800 font-sans">{record.project_name || record.projectName}</span>
                        <span className="text-slate-300">/</span>
                        <span className="text-indigo-600 border border-indigo-100 bg-indigo-50/50 px-1.5 py-0.2 rounded-xs">
                          {record.branch} @ {record.last_commit_id?.slice(0, 10) || record.commitHash}
                        </span>
                        <span className="text-slate-300">|</span>
                        <span className="text-slate-500 bg-slate-100 px-1.5 rounded-xs">
                          事件类型: {record.event_type}
                        </span>
                        <span className="text-slate-300">|</span>
                        <span className="text-slate-500">
                          核心托管: {record.platform_type}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-900">{record.title || record.prTitle}</h3>
                    </div>

                    {/* Summary commentary line with compressed vertical padding */}
                    <div className="py-2 px-3.5 rounded-xl border border-slate-150 bg-slate-50/50 text-xs text-slate-600 leading-relaxed font-light">
                      <div className="font-bold text-slate-800 flex items-center justify-between mb-1">
                        <span className="flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
                          <span>AI 报告诊断意见 (review_result):</span>
                        </span>
                        <div className="flex gap-2 text-[9px] font-mono text-slate-400">
                          <span className="text-emerald-500">+{record.additions} insertions</span>
                          <span className="text-red-500">-{record.deletions} deletions</span>
                        </div>
                      </div>
                      {record.summary}
                    </div>

                    {/* Commit info line */}
                    <div className="flex items-center gap-4 text-[11px] text-slate-450 font-light font-mono">
                      <span className="font-medium text-slate-500 flex items-center gap-1">
                        <span>提交开发者:</span>
                        <span className="text-slate-700 font-bold">{committerName}</span>
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" />
                        <span>发生于: {record.created_at}</span>
                      </span>
                      <span>•</span>
                      <span>通知下发 (delivery_status): 
                        <span className={`ml-1 font-bold ${record.delivery_status === 'sent' ? 'text-emerald-600' : 'text-amber-600'}`}>
                          {record.delivery_status === 'sent' ? 'SENT' : 'PENDING'}
                        </span>
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-2 shrink-0 uppercase tracking-widest text-[9px] font-bold">
                    <div className="text-right">
                      <span className="text-slate-400 block mb-0.5">SCORE评分</span>
                      <span
                        className={`text-2xl font-mono px-3.5 py-1.5 rounded-xl border block ${
                          scoreStatus === 'excellent'
                            ? 'text-emerald-700 bg-emerald-50 border-emerald-200 font-bold'
                            : scoreStatus === 'pass'
                            ? 'text-indigo-700 bg-indigo-50 border-indigo-200 font-bold'
                            : scoreStatus === 'warning'
                            ? 'text-amber-700 bg-amber-50 border-amber-200 font-bold'
                            : 'text-red-700 bg-red-50 border-red-200 font-bold'
                        }`}
                      >
                        {record.score}分
                      </span>
                    </div>

                    {(record.robotNotifiedView || record.robotNotified) && (
                      <span className="text-[8.5px] tracking-normal font-medium bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-md border border-emerald-100">
                        已自动同步 IM 机器人通道
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Pagination Controls */}
        {totalItems > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-100 bg-white px-6 py-4 text-xs gap-4 select-none shadow-3xs">
            <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
              <div>
                显示 <span className="font-semibold text-slate-800">{indexOfFirstItem + 1}</span> 至{' '}
                <span className="font-semibold text-slate-800">{Math.min(indexOfLastItem, totalItems)}</span> 条，
                共 <span className="font-semibold text-slate-800">{totalItems}</span> 条审查记录
              </div>
              <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                <span>每页显示:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="border border-slate-205 bg-slate-50 text-slate-850 rounded-md px-2 py-1 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                >
                  <option value={5}>5 条</option>
                  <option value={10}>10 条</option>
                  <option value={20}>20 条</option>
                  <option value={50}>50 条</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>上一页</span>
              </button>
              <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                <span className="font-bold text-indigo-600">{currentPage}</span>
                <span className="text-slate-300">/</span>
                <span>{totalPages}</span>
              </div>
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
              >
                <span>下一页</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ==========================================================
 * 3. TEAM MEMBER ANALYSIS (成员分析 - project_members)
 * ========================================================== */
export function MemberAnalysisView() {
  const members = [
    { id: 'mem-101', name: 'jdw-art', email: 'jdw-art@gmail.com', level: '架构组组长', codeChangeLine: 2540, kpi: '98.2%', is_active: true, created_at: '2026-05-01' },
    { id: 'mem-102', name: 'admin', email: 'admin@ai-reviewer.org', level: '项目运维负责人', codeChangeLine: 1205, kpi: '100%', is_active: true, created_at: '2026-05-02' },
    { id: 'mem-103', name: 'system-agent', email: 'system-agent@ai-reviewer.org', level: '智能核算代理人', codeChangeLine: 450, kpi: '75.0%', is_active: true, created_at: '2026-05-10' },
  ];

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs">
        <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
          <Users className="w-4 h-4 text-indigo-500 shrink-0" />
          <span>团队代码提交活跃与规范分析</span>
        </h2>
        <p className="text-[11px] text-slate-500 mt-0.5">
          监控各核心仓库映射的成员属性和指标排行。数据字段来自 <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-650 font-mono">project_members</code> 表模型。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Ranked Table */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center justify-between">
            <span>开发组成员质量矩阵 (project_members)</span>
            <span className="text-[10px] text-slate-400 font-mono">(active: true)</span>
          </h3>
          <div className="space-y-4">
            {members.map((m) => (
              <div key={m.id} className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center flex-wrap gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-full font-bold text-xs uppercase flex items-center justify-center">
                    {m.name.slice(0, 2)}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                      <span>{m.name}</span>
                      <span className="text-[9px] bg-slate-200 text-slate-550 px-1 rounded-sm font-mono font-normal">
                        Role: {m.level}
                      </span>
                    </h4>
                    <p className="text-[10px] text-slate-450 font-mono mt-0.5">{m.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-right text-xs">
                  <div>
                    <span className="text-[9px] text-slate-400 block font-mono">member_id</span>
                    <span className="font-mono text-slate-600 font-bold">{m.id}</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-slate-400 block">通过度</span>
                    <span className="font-mono font-bold text-indigo-600">{m.kpi}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Dynamic Metric card charts */}
        <div className="bg-[#0b0c16] text-[#93c5fd] rounded-2xl p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-white">
              <Award className="w-5 h-5 text-indigo-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider">智能审计风险追踪</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-light">
              近期 review_records 审查表明，jdw-art 开发者提交的代码架构稳定，AST 宏分析通过率极高。系统代理审计拦截模型未检测出核心敏感字段泄漏。
            </p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-2 mt-4 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">平均风险评估级 (Average Risk)</span>
              <span className="text-emerald-400 font-bold">1.05 (LOW RISK)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">系统判定决策值 (Decision Engine)</span>
              <span className="text-indigo-300 font-bold">BLOCK-FREE / AUTOMERGE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ==========================================================
 * 4. SYSTEM SECURITY ACCESS CENTER (RBAC MATRIX - users, roles, permissions)
 * ========================================================== */

export const allPermissions = [
  { id: 1, name: "查看仪表盘", code: "dashboard:read", resource: "dashboard", action: "read", description: "允许查看后台仪表盘概览统计。", is_system: true },
  { id: 2, name: "查看项目", code: "project:read", resource: "project", action: "read", description: "允许查看项目列表与详情。", is_system: true },
  { id: 3, name: "创建项目", code: "project:create", resource: "project", action: "create", description: "允许创建后台管理项目。", is_system: true },
  { id: 4, name: "更新项目", code: "project:update", resource: "project", action: "update", description: "允许更新项目基本信息与绑定关系。", is_system: true },
  { id: 5, name: "启停项目", code: "project:status", resource: "project", action: "status", description: "允许启用或停用项目。", is_system: true },
  { id: 6, name: "查看项目模板", code: "project_template:read", resource: "project_template", action: "read", description: "允许查看项目模板列表与详情。", is_system: true },
  { id: 7, name: "创建项目模板", code: "project_template:create", resource: "project_template", action: "create", description: "允许创建项目模板。", is_system: true },
  { id: 8, name: "更新项目模板", code: "project_template:update", resource: "project_template", action: "update", description: "允许更新项目模板内容。", is_system: true },
  { id: 9, name: "启停项目模板", code: "project_template:status", resource: "project_template", action: "status", description: "允许启用或停用项目模板。", is_system: true },
  { id: 10, name: "查看模型配置", code: "llm_model:read", resource: "llm_model", action: "read", description: "允许查看大模型配置列表与详情。", is_system: true },
  { id: 11, name: "创建模型配置", code: "llm_model:create", resource: "llm_model", action: "create", description: "允许创建大模型配置。", is_system: true },
  { id: 12, name: "更新模型配置", code: "llm_model:update", resource: "llm_model", action: "update", description: "允许更新大模型配置。", is_system: true },
  { id: 13, name: "启停模型配置", code: "llm_model:status", resource: "llm_model", action: "status", description: "允许启用或停用大模型配置。", is_system: true },
  { id: 14, name: "查看通知机器人", code: "notification_bot:read", resource: "notification_bot", action: "read", description: "允许查看通知机器人列表与详情。", is_system: true },
  { id: 15, name: "创建通知机器人", code: "notification_bot:create", resource: "notification_bot", action: "create", description: "允许创建通知机器人。", is_system: true },
  { id: 16, name: "更新通知机器人", code: "notification_bot:update", resource: "notification_bot", action: "update", description: "允许更新通知机器人配置。", is_system: true },
  { id: 17, name: "启停通知机器人", code: "notification_bot:status", resource: "notification_bot", action: "status", description: "允许启用或停用通知机器人。", is_system: true },
  { id: 18, name: "查看审查记录", code: "review_record:read", resource: "review_record", action: "read", description: "允许查看审查记录列表与详情。", is_system: true },
  { id: 19, name: "查看审查记录原始数据", code: "review_record:raw", resource: "review_record", action: "raw", description: "允许查看审查记录原始 webhook 与 agent trace 数据。", is_system: true },
  { id: 20, name: "导入审查记录", code: "review_record:import", resource: "review_record", action: "import", description: "允许导入 mock 审查事件并生成审查记录。", is_system: true },
  { id: 21, name: "查看成员分析", code: "member_analytics:read", resource: "member_analytics", action: "read", description: "允许查看成员分析统计结果。", is_system: true },
  { id: 22, name: "查看审计日志", code: "audit_log:read", resource: "audit_log", action: "read", description: "允许查看后台操作审计日志。", is_system: true },
  { id: 23, name: "查看用户", code: "user:read", resource: "user", action: "read", description: "允许查看后台用户列表与详情。", is_system: true },
  { id: 24, name: "创建用户", code: "user:create", resource: "user", action: "create", description: "允许创建后台用户。", is_system: true },
  { id: 25, name: "更新用户", code: "user:update", resource: "user", action: "update", description: "允许更新后台用户资料。", is_system: true },
  { id: 26, name: "修改用户状态", code: "user:status", resource: "user", action: "status", description: "允许启用或禁用后台用户。", is_system: true },
  { id: 27, name: "重置用户密码", code: "user:reset-password", resource: "user", action: "reset-password", description: "允许重置后台用户密码。", is_system: true },
  { id: 28, name: "分配用户角色", code: "user:assign-role", resource: "user", action: "assign-role", description: "允许为后台用户分配角色。", is_system: true },
  { id: 29, name: "查看角色", code: "role:read", resource: "role", action: "read", description: "允许查看角色列表与详情。", is_system: true },
  { id: 30, name: "创建角色", code: "role:create", resource: "role", action: "create", description: "允许创建角色。", is_system: true },
  { id: 31, name: "更新角色", code: "role:update", resource: "role", action: "update", description: "允许更新角色信息。", is_system: true },
  { id: 32, name: "删除角色", code: "role:delete", resource: "role", action: "delete", description: "允许删除非系统角色。", is_system: true },
  { id: 33, name: "分配角色权限与菜单", code: "role:assign", resource: "role", action: "assign", description: "允许为角色分配权限与菜单。", is_system: true },
  { id: 34, name: "查看菜单", code: "menu:read", resource: "menu", action: "read", description: "允许查看后台菜单。", is_system: true },
  { id: 35, name: "创建菜单", code: "menu:create", resource: "menu", action: "create", description: "允许创建后台菜单。", is_system: true },
  { id: 36, name: "更新菜单", code: "menu:update", resource: "menu", action: "update", description: "允许更新后台菜单。", is_system: true },
  { id: 37, name: "删除菜单", code: "menu:delete", resource: "menu", action: "delete", description: "允许删除非系统菜单。", is_system: true },
  { id: 38, name: "删除用户", code: "user:delete", resource: "user", action: "delete", description: "允许删除后台用户，但不允许删除自己或最后一个超级管理员。", is_system: true }
];

export const allMenus = [
  { id: 1, parent_id: null, name: "仪表盘", path: "/dashboard", component: "dashboard/DashboardOverviewPage", icon: "LayoutDashboard", sort: 100, visible: true, is_system: true },
  { id: 2, parent_id: null, name: "项目管理", path: "/projects", component: "projects/ProjectListPage", icon: "FolderCode", sort: 110, visible: true, is_system: true },
  { id: 3, parent_id: 2, name: "项目模板管理", path: "/project-templates", component: "projects/ProjectTemplateListPage", icon: "FileJson", sort: 120, visible: true, is_system: true },
  { id: 4, parent_id: null, name: "模型管理", path: "/models", component: "models/ModelListPage", icon: "Cpu", sort: 130, visible: true, is_system: true },
  { id: 5, parent_id: null, name: "通知机器人", path: "/notification-bots", component: "notifications/NotificationBotListPage", icon: "Bot", sort: 140, visible: true, is_system: true },
  { id: 6, parent_id: null, name: "审查记录", path: "/review-records", component: "reviews/ReviewRecordListPage", icon: "BookmarkCheck", sort: 150, visible: true, is_system: true },
  { id: 7, parent_id: null, name: "成员分析", path: "/member-analytics", component: "reviews/MemberAnalyticsPage", icon: "Users", sort: 160, visible: true, is_system: true },
  { id: 8, parent_id: null, name: "系统日志", path: "/audit-logs", component: "system/AuditLogPage", icon: "ScrollText", sort: 180, visible: true, is_system: true },
  { id: 9, parent_id: null, name: "权限管理", path: "/system", component: "system/SystemLayoutPage", icon: "ShieldAlert", sort: 170, visible: true, is_system: true },
  { id: 10, parent_id: 9, name: "用户管理", path: "/system/users", component: "system/UserListPage", icon: "UserCheck", sort: 171, visible: true, is_system: true },
  { id: 11, parent_id: 9, name: "角色管理", path: "/system/roles", component: "system/RoleListPage", icon: "ShieldCheck", sort: 172, visible: true, is_system: true }
];

const resourceGroupNames: Record<string, string> = {
  dashboard: '仪表盘概览',
  project: '项目库管控',
  project_template: '基础项目模板',
  llm_model: 'LLM 大模型定义',
  notification_bot: '信息推送机器人',
  review_record: 'AI 审查记录溯源',
  member_analytics: '成员研发效能',
  audit_log: '安全运行审计',
  user: '后台用户运维',
  role: '角标角色权限控制',
  menu: '动态菜单配置'
};

export function RBACMatrixView({
  tabId,
  onAddLog,
}: {
  tabId: 'users' | 'roles';
  onAddLog?: (action: string, text: string) => void;
}) {
  const [usersList, setUsersList] = useState([
    { id: '1', username: 'admin', nickname: '', email: '', phone: '', is_superuser: true, is_active: true, last_login_at: '2026-06-04 11:32', assigned_roles: ['SUPER_ADMIN'] },
    { id: '2', username: 'user01', nickname: 'user01', email: '', phone: '', is_superuser: false, is_active: true, last_login_at: '2026-05-12 10:00', assigned_roles: ['NORMAL_USER'] },
    { id: '3', username: 'jdw-art', nickname: 'jdw-art', email: 'jdw_art@163.com', phone: '13812345678', is_superuser: true, is_active: true, last_login_at: '2026-06-04 15:15', assigned_roles: ['SUPER_ADMIN'] },
    { id: '4', username: 'auditor', nickname: '外部安全审计官', email: 'auditor@company.com', phone: '13799988888', is_superuser: false, is_active: true, last_login_at: '2026-06-02 18:20', assigned_roles: ['SECURITY_AUDITOR'] },
  ]);

  // Pagination states
  const [userPage, setUserPage] = useState(1);
  const [rolePage, setRolePage] = useState(1);
  const [userPageSize, setUserPageSize] = useState(5);
  const [rolePageSize, setRolePageSize] = useState(5);

  const totalUsers = usersList.length;
  const totalUserPages = Math.ceil(totalUsers / userPageSize) || 1;
  const indexOfLastUser = userPage * userPageSize;
  const indexOfFirstUser = Math.max(0, indexOfLastUser - userPageSize);
  const currentUsers = usersList.slice(indexOfFirstUser, indexOfLastUser);

  const toggleUserActive = (id: string, username: string, currentStatus: boolean) => {
    setUsersList(
      usersList.map((u) => (u.id === id ? { ...u, is_active: !u.is_active } : u))
    );
    if (onAddLog) {
      onAddLog(
        'USER_STATE_TOGGLED',
        `管理员修改用户 ${username} 的状态为: ${!currentStatus ? '活跃 (ACTIVE)' : '禁用 (MUTED)'}`
      );
    }
  };

  const [rolesList, setRolesList] = useState<any[]>([
    { 
      id: '1', 
      name: 'Super Admin', 
      code: 'SUPER_ADMIN', 
      description: 'System bootstrap role with full administrative access. Granted master keys.', 
      is_system: true, 
      created_at: '2026-01-01', 
      permissions: allPermissions.map(p => p.code), 
      menus: allMenus.map(m => m.id) 
    },
    { 
      id: '2', 
      name: 'Normal User', 
      code: 'NORMAL_USER', 
      description: '普通开发成员。可阅览授权项目与智能审查报告详情。', 
      is_system: false, 
      created_at: '2026-01-02', 
      permissions: ['dashboard:read', 'project:read', 'project_template:read', 'llm_model:read', 'review_record:read'], 
      menus: [1, 2, 3, 4, 6] 
    },
    { 
      id: '3', 
      name: 'Security Auditor', 
      code: 'SECURITY_AUDITOR', 
      description: '信息安全合规审计。专责调阅后台操作审计日志流和完整的审查记录。', 
      is_system: true, 
      created_at: '2026-02-15', 
      permissions: ['dashboard:read', 'audit_log:read', 'review_record:read', 'review_record:raw', 'member_analytics:read'], 
      menus: [1, 6, 7, 8] 
    },
  ]);

  const totalRoles = rolesList.length;
  const totalRolePages = Math.ceil(totalRoles / rolePageSize) || 1;
  const indexOfLastRole = rolePage * rolePageSize;
  const indexOfFirstRole = Math.max(0, indexOfLastRole - rolePageSize);
  const currentRoles = rolesList.slice(indexOfFirstRole, indexOfLastRole);

  // Drawer / Editing States for Users
  const [editingUser, setEditingUser] = useState<any | null>(null);
  const [editNickname, setEditNickname] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editIsSuperuser, setEditIsSuperuser] = useState(false);
  const [editRoles, setEditRoles] = useState<string[]>([]);

  // Editing States for Roles
  const [editingRole, setEditingRole] = useState<any | null>(null);
  const [editRoleName, setEditRoleName] = useState('');
  const [editRoleCode, setEditRoleCode] = useState('');
  const [editRoleDesc, setEditRoleDesc] = useState('');
  const [editRoleIsSystem, setEditRoleIsSystem] = useState(false);
  const [editRolePermissions, setEditRolePermissions] = useState<string[]>([]);
  const [editRoleMenus, setEditRoleMenus] = useState<number[]>([]);
  const [validationError, setValidationError] = useState('');

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (editingUser) setEditingUser(null);
        if (editingRole) setEditingRole(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [editingUser ? editingUser.id : '', editingRole ? editingRole.id : '']);

  const startEditUser = (user: any) => {
    setEditingUser(user);
    setEditNickname(user.nickname || '');
    setEditEmail(user.email || '');
    setEditPhone(user.phone || '');
    setEditIsSuperuser(user.is_superuser ?? false);
    setEditRoles(user.assigned_roles || []);
  };

  const handleSaveUser = () => {
    if (!editingUser) return;

    setUsersList(
      usersList.map((u) => {
        if (u.id === editingUser.id) {
          return {
            ...u,
            nickname: editNickname,
            email: editEmail,
            phone: editPhone,
            is_superuser: editIsSuperuser,
            assigned_roles: editRoles,
          };
        }
        return u;
      })
    );

    if (onAddLog) {
      onAddLog(
        'USER_PROFILE_MUTATED',
        `管理员编辑了用户账号: ${editingUser.username}。昵称: "${editNickname || '—'}"，超管标记: ${
          editIsSuperuser ? '启用' : '禁用'
        }，分配角色: [${editRoles.join(', ') || 'Normal User'}]`
      );
    }

    setEditingUser(null);
  };

  const startEditRole = (role: any) => {
    setValidationError('');
    setEditingRole(role);
    setEditRoleName(role.name || '');
    setEditRoleCode(role.code || '');
    setEditRoleDesc(role.description || '');
    setEditRoleIsSystem(role.is_system || false);
    setEditRolePermissions(role.permissions || []);
    setEditRoleMenus(role.menus || []);
  };

  const startCreateRole = () => {
    setValidationError('');
    setEditingRole({ id: 'new', isNew: true });
    setEditRoleName('');
    setEditRoleCode('');
    setEditRoleDesc('');
    setEditRoleIsSystem(false);
    setEditRolePermissions([]);
    setEditRoleMenus([]);
  };

  const handleSaveRole = () => {
    if (!editingRole) return;

    if (!editRoleName.trim()) {
      setValidationError('角色名称不能为空！');
      return;
    }
    if (!editRoleCode.trim()) {
      setValidationError('角色唯一编码不能为空！');
      return;
    }

    const formattedCode = editRoleCode.toUpperCase().trim();

    if (editingRole.isNew) {
      const codeExists = rolesList.some(r => r.code === formattedCode);
      if (codeExists) {
        setValidationError(`角色唯一编码 [${formattedCode}] 已被占用，请更换！`);
        return;
      }

      const newRole = {
        id: String(Date.now()),
        name: editRoleName.trim(),
        code: formattedCode,
        description: editRoleDesc.trim(),
        is_system: editRoleIsSystem,
        created_at: new Date().toISOString().split('T')[0],
        permissions: editRolePermissions,
        menus: editRoleMenus
      };

      setRolesList([...rolesList, newRole]);

      if (onAddLog) {
        onAddLog(
          'ROLE_CREATED',
          `管理员创建了全新安全角色: "${editRoleName}" [${formattedCode}]，关联权限数: ${editRolePermissions.length}，授权菜单路由数: ${editRoleMenus.length}`
        );
      }
    } else {
      setRolesList(
        rolesList.map(r => r.id === editingRole.id ? {
          ...r,
          name: editRoleName.trim(),
          code: r.is_system ? r.code : formattedCode,
          description: editRoleDesc.trim(),
          permissions: editRolePermissions,
          menus: editRoleMenus
        } : r)
      );

      if (onAddLog) {
        onAddLog(
          'ROLE_MUTATED',
          `管理员更新了系统角色: "${editRoleName}" [${editingRole.is_system ? editingRole.code : formattedCode}]。分配功能权限数: ${editRolePermissions.length}，授权菜单数: ${editRoleMenus.length}`
        );
      }
    }

    setEditingRole(null);
  };

  const handleDeleteRole = (id: string, code: string, isSystem: boolean) => {
    if (isSystem) {
      alert('系统内置预设定角色，属于系统安全运行基座，不支持任何物理删除操作！');
      return;
    }

    if (confirm(`深度警示：您此操作将彻底物理删除自定义角色 [${code}]。\n相关已挂载该角色的用户会立即丧失对应准入能力！您确定要继续吗？`)) {
      setRolesList(rolesList.filter(r => r.id !== id));
      if (onAddLog) {
        onAddLog('ROLE_DELETED', `管理员物理删除了自定义角色: [${code}]。相关用户挂载已被剥离。`);
      }
    }
  };

  const getRolesDisplay = (assignedCodes?: string[]) => {
    if (!assignedCodes || assignedCodes.length === 0) {
      return <span className="text-slate-400">Normal User</span>;
    }
    return assignedCodes
      .map((code) => {
        const match = rolesList.find((r) => r.code === code);
        return match ? match.name : code;
      })
      .join(', ');
  };

  const renderMenuIcon = (iconName: string) => {
    const IconComponent = (Lucide as any)[iconName] || ShieldCheck;
    return <IconComponent className="w-4 h-4 text-indigo-500" />;
  };

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs">
        <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
          <KeyRound className="w-4 h-4 text-indigo-500 shrink-0" />
          <span>RBAC 角色权限与路由控制模块</span>
        </h2>
        <p className="text-[11px] text-slate-500 mt-0.5">
          管控系统的准入规则。数据列约束和唯一索引等已在 PostgreSQL SQL 等效实体中严格确立：
        </p>
      </div>

      {tabId === 'users' ? (
        <div className="space-y-6">
          {/* Users Table Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden w-full">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <div className="space-y-0.5">
                <h3 className="text-xs font-bold text-slate-800 font-mono uppercase">用户管理</h3>
                <p className="text-[10px] text-slate-400">查看系统用户账号、角色分配和启用状态</p>
              </div>
              <span className="text-[10px] text-indigo-600 font-semibold font-mono bg-indigo-50 border border-indigo-100/50 px-2 py-0.5 rounded-sm">
                Active Users ({usersList.filter(u => u.is_active).length})
              </span>
            </div>
            <div className="overflow-x-auto scrollbar-none">
              <table className="w-full text-left border-collapse whitespace-nowrap text-xs">
                <thead>
                  <tr className="bg-slate-50/50 text-slate-400 font-bold border-b border-slate-100">
                    <th className="py-3 px-6">用户名</th>
                    <th className="py-3 px-6">昵称</th>
                    <th className="py-3 px-6">邮箱</th>
                    <th className="py-3 px-6">角色</th>
                    <th className="py-3 px-6">超管</th>
                    <th className="py-3 px-6">状态</th>
                    <th className="py-3 px-6 text-right">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {currentUsers.map((u) => {
                    const isSelected = editingUser?.id === u.id;
                    return (
                      <tr 
                        key={u.id} 
                        className={`hover:bg-slate-50/40 transition-colors ${
                          isSelected ? 'bg-indigo-50/50 hover:bg-indigo-50/70' : ''
                        }`}
                      >
                        <td className="py-3.5 px-6 font-semibold font-mono text-slate-900">{u.username}</td>
                        <td className="py-3.5 px-6 text-slate-600 font-medium">{u.nickname || '—'}</td>
                        <td className="py-3.5 px-6 text-slate-500 font-mono text-[11px]">
                          {u.email ? (
                            <span className="flex items-center gap-1.5">
                              <Mail className="w-3 h-3 text-slate-300" />
                              <span>{u.email}</span>
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-6 text-slate-755 font-medium">
                          <span className="bg-indigo-50/60 text-indigo-700 px-2.5 py-0.5 rounded-full text-[10px] border border-indigo-100/50 shadow-2xs">
                            {getRolesDisplay(u.assigned_roles)}
                          </span>
                        </td>
                        <td className="py-3.5 px-6">
                          <span className={`px-2 py-0.5 rounded-sm font-bold text-[10px] uppercase ${u.is_superuser ? 'bg-indigo-50 text-indigo-600 border border-indigo-100' : 'bg-slate-100 text-slate-400'}`}>
                            {u.is_superuser ? 'SUPER' : 'COMMON'}
                          </span>
                        </td>
                        <td className="py-3.5 px-6 font-mono">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleUserActive(u.id, u.username, u.is_active);
                            }}
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold cursor-pointer transition-colors ${u.is_active ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-red-50 text-red-500 border border-red-100'}`}
                          >
                            {u.is_active ? 'ACTIVE' : 'DISABLED'}
                          </button>
                        </td>
                        <td className="py-3.5 px-6 text-right">
                          <button
                            onClick={() => startEditUser(u)}
                            className="px-3 py-1 bg-white hover:bg-slate-50 text-slate-700 hover:text-indigo-600 border border-slate-200/80 rounded-lg text-[11px] font-semibold transition-all shadow-2xs hover:shadow-sm cursor-pointer"
                          >
                            编辑
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {/* Users Pagination controls */}
            {totalUsers > 0 && (
              <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-100 bg-white px-6 py-4 text-xs gap-4 select-none">
                <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
                  <div>
                    显示 <span className="font-semibold text-slate-800">{indexOfFirstUser + 1}</span> 至{' '}
                    <span className="font-semibold text-slate-800">{Math.min(indexOfLastUser, totalUsers)}</span> 条，
                    共 <span className="font-semibold text-slate-800">{totalUsers}</span> 个用户
                  </div>
                  <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                    <span>每页显示:</span>
                    <select
                      value={userPageSize}
                      onChange={(e) => {
                        setUserPageSize(Number(e.target.value));
                        setUserPage(1);
                      }}
                      className="border border-slate-200 bg-slate-50 text-slate-850 rounded-md px-1.5 py-0.5 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                    >
                      <option value={3}>3 条</option>
                      <option value={5}>5 条</option>
                      <option value={10}>10 条</option>
                      <option value={20}>20 条</option>
                    </select>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setUserPage((prev) => Math.max(prev - 1, 1))}
                    disabled={userPage === 1}
                    className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    <span>上一页</span>
                  </button>
                  <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                    <span className="font-bold text-indigo-600">{userPage}</span>
                    <span className="text-slate-300">/</span>
                    <span>{totalUserPages}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setUserPage((prev) => Math.min(prev + 1, totalUserPages))}
                    disabled={userPage === totalUserPages}
                    className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                  >
                    <span>下一页</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Edit Dialog Modal Overlay */}
          <AnimatePresence>
            {editingUser && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                {/* Backdrop Layer */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setEditingUser(null)}
                  className="absolute inset-0 bg-slate-900/45 backdrop-blur-xs"
                />

                {/* Modal Layout Box */}
                <motion.div
                  initial={{ scale: 0.96, y: 12, opacity: 0 }}
                  animate={{ scale: 1, y: 0, opacity: 1 }}
                  exit={{ scale: 0.96, y: 12, opacity: 0 }}
                  transition={{ type: 'spring', duration: 0.35, bounce: 0.1 }}
                  className="relative w-full max-w-lg bg-white rounded-2xl border border-slate-200/80 shadow-2xl overflow-hidden z-10 flex flex-col max-h-[85vh]"
                >
                  {/* Header */}
                  <div className="px-6 py-4.5 border-b border-slate-100 flex justify-between items-center bg-slate-50/65">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
                        <h3 className="text-sm font-bold text-slate-800">编辑用户角色与信息</h3>
                      </div>
                      <p className="text-[10px] text-slate-400 leading-normal">维护用户账户对应的联系资料、安全标记和角色授权</p>
                    </div>
                    <button
                      onClick={() => setEditingUser(null)}
                      className="p-1.5 hover:bg-slate-100 text-slate-400 hover:text-slate-600 rounded-lg transition-all cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Body Content (Scrollable for compact heights) */}
                  <div className="p-6 space-y-4 overflow-y-auto max-h-[50vh] md:max-h-[55vh] scrollbar-thin">
                    <div className="space-y-1.5">
                      <label className="text-[10px] uppercase font-bold text-slate-500 block font-mono">用户名 (username)</label>
                      <div className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 font-mono text-xs select-all">
                        {editingUser.username}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10.5px] font-bold text-slate-700 block">昵称</label>
                      <input
                        type="text"
                        value={editNickname}
                        onChange={(e) => setEditNickname(e.target.value)}
                        className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all"
                        placeholder="请输入昵称"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10.5px] font-bold text-slate-700 block">邮箱</label>
                      <input
                        type="text"
                        value={editEmail}
                        onChange={(e) => setEditEmail(e.target.value)}
                        className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all"
                        placeholder="请输入邮箱地址"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10.5px] font-bold text-slate-700 block">手机号</label>
                      <input
                        type="text"
                        value={editPhone}
                        onChange={(e) => setEditPhone(e.target.value)}
                        className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all"
                        placeholder="请输入手机号"
                      />
                    </div>

                    <label className="flex items-center gap-3 p-3.5 bg-slate-50/50 border border-slate-200 rounded-xl hover:bg-slate-50 cursor-pointer select-none transition-colors">
                      <input
                        type="checkbox"
                        checked={editIsSuperuser}
                        onChange={(e) => setEditIsSuperuser(e.target.checked)}
                        className="w-4 h-4 text-indigo-600 border-slate-350 focus:ring-indigo-500 rounded cursor-pointer"
                      />
                      <span className="text-xs font-bold text-slate-800">设为超级管理员 (is_superuser)</span>
                    </label>

                    {/* Role allocation list */}
                    <div className="space-y-2.5">
                      <label className="text-[10.5px] font-bold text-slate-700 block">角色分配</label>
                      <div className="space-y-2.5">
                        {rolesList.map((role) => {
                          const isRoleSelected = editRoles.includes(role.code);
                          return (
                            <label
                              key={role.id}
                              className={`flex items-start gap-3 p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
                                isRoleSelected
                                  ? 'bg-indigo-50/45 border-indigo-200 ring-2 ring-indigo-500/5'
                                  : 'bg-white border-slate-200 hover:bg-slate-50/50'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={isRoleSelected}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setEditRoles([...editRoles, role.code]);
                                  } else {
                                    setEditRoles(editRoles.filter((c) => c !== role.code));
                                  }
                                }}
                                className="mt-1 w-4 h-4 text-indigo-600 border-slate-300 focus:ring-indigo-500 rounded cursor-pointer transition-all"
                              />
                              <div className="space-y-0.5">
                                <div className="text-xs font-bold text-slate-800 flex items-center gap-2">
                                  <span>{role.name}</span>
                                  <span className="text-[9px] font-mono text-slate-400 bg-slate-100 px-1 py-0.2 rounded font-semibold uppercase">
                                    {role.code}
                                  </span>
                                </div>
                                <p className="text-[10.5px] text-slate-450 font-light leading-relaxed">
                                  {role.description}
                                </p>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Footer actions */}
                  <div className="px-6 py-4.5 border-t border-slate-100 bg-slate-50/30 flex justify-end gap-3">
                    <button
                      onClick={() => setEditingUser(null)}
                      className="px-4 py-2 bg-white hover:bg-slate-50 active:bg-slate-100 border border-slate-200 text-slate-650 text-xs font-semibold rounded-xl transition-all cursor-pointer"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSaveUser}
                      className="px-5 py-2.5 bg-[#0b0c16] text-[#93c5fd] hover:bg-[#121424] active:bg-[#06070c] border border-[#2b3558] text-xs font-bold rounded-xl transition-all shadow-xs cursor-pointer"
                    >
                      保存修改
                    </button>
                  </div>
                </motion.div>
              </div>
            )}
          </AnimatePresence>
        </div>
      ) : tabId === 'roles' ? (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <div className="space-y-0.5">
                <h3 className="text-xs font-bold text-slate-800 font-mono uppercase">全局角色配置表 (roles)</h3>
                <p className="text-[10px] text-slate-400">唯一代码映射 code 关联功能权限与动态菜单路由</p>
              </div>
              <button
                onClick={startCreateRole}
                className="px-3.5 py-1.5 bg-[#0b0c16] hover:bg-[#181a2e] text-[#93c5fd] border border-[#232b4b] rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
              >
                <PlusCircle className="w-4 h-4" />
                <span>新增系统角色</span>
              </button>
            </div>
            <div className="overflow-x-auto scrollbar-none">
              <table className="w-full text-left border-collapse whitespace-nowrap text-xs">
                <thead>
                  <tr className="bg-slate-50/50 text-slate-400 font-bold border-b border-slate-100">
                    <th className="py-3 px-6">ID</th>
                    <th className="py-3 px-6">角色标签 (name)</th>
                    <th className="py-3 px-6">唯一代码标识 (code)</th>
                    <th className="py-3 px-6">功能权限数</th>
                    <th className="py-3 px-6">展示菜单数</th>
                    <th className="py-3 px-6">预设系统(is_system)</th>
                    <th className="py-3 px-6">规则详情 / 描述 (description)</th>
                    <th className="py-3 px-6">生成日期</th>
                    <th className="py-3 px-6 text-right">管理操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {currentRoles.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/40">
                      <td className="py-3.5 px-6 font-mono text-slate-500">{r.id}</td>
                      <td className="py-3.5 px-6 font-bold text-slate-800">{r.name}</td>
                      <td className="py-3.5 px-6 font-semibold font-mono text-indigo-650">
                        <span className="bg-slate-100 px-2 py-0.5 rounded text-[10.5px]">{r.code}</span>
                      </td>
                      <td className="py-3.5 px-6 font-mono">
                        <span className="bg-emerald-50 text-emerald-800 border border-emerald-100 px-2 py-0.5 rounded font-bold text-[10.5px]">
                          {(r.permissions || []).length} / 38 项
                        </span>
                      </td>
                      <td className="py-3.5 px-6 font-mono">
                        <span className="bg-blue-50 text-blue-800 border border-blue-100 px-2 py-0.5 rounded font-bold text-[10.5px]">
                          {(r.menus || []).length} / 11 个
                        </span>
                      </td>
                      <td className="py-3.5 px-6">
                        <span className={`px-2 py-0.5 rounded-sm font-bold text-[9px] uppercase ${r.is_system ? 'bg-indigo-50 text-indigo-600 border border-indigo-100' : 'bg-slate-100 text-slate-400'}`}>
                          {r.is_system ? 'SYSTEM' : 'CUSTOM'}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 text-slate-550 max-w-xs font-light text-[11.5px] whitespace-normal leading-relaxed">{r.description}</td>
                      <td className="py-3.5 px-6 text-slate-450 font-mono text-[11px]">{r.created_at}</td>
                      <td className="py-3.5 px-6 text-right space-x-2">
                        <button
                          onClick={() => startEditRole(r)}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 hover:text-indigo-600 border border-slate-200 rounded-lg text-[11px] font-semibold transition-all shadow-3xs cursor-pointer"
                        >
                          控制分配
                        </button>
                        <button
                          onClick={() => handleDeleteRole(r.id, r.code, r.is_system)}
                          disabled={r.is_system}
                          className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-all ${
                            r.is_system 
                              ? 'bg-slate-50 text-slate-350 border-slate-100 cursor-not-allowed'
                              : 'bg-red-50 hover:bg-red-100 text-red-600 border-red-150 cursor-pointer'
                          }`}
                          title={r.is_system ? "内置核心角色，拒绝删除" : "删除角色"}
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Roles Pagination controls */}
            {totalRoles > 0 && (
              <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-100 bg-white px-6 py-4 text-xs gap-4 select-none">
                <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
                  <div>
                    显示 <span className="font-semibold text-slate-800">{indexOfFirstRole + 1}</span> 至{' '}
                    <span className="font-semibold text-slate-800">{Math.min(indexOfLastRole, totalRoles)}</span> 条，
                    共 <span className="font-semibold text-slate-800">{totalRoles}</span> 个角色
                  </div>
                  <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                    <span>每页显示:</span>
                    <select
                      value={rolePageSize}
                      onChange={(e) => {
                        setRolePageSize(Number(e.target.value));
                        setRolePage(1);
                      }}
                      className="border border-slate-200 bg-slate-50 text-slate-850 rounded-md px-1.5 py-0.5 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                    >
                      <option value={3}>3 条</option>
                      <option value={5}>5 条</option>
                      <option value={10}>10 条</option>
                      <option value={20}>20 条</option>
                    </select>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setRolePage((prev) => Math.max(prev - 1, 1))}
                    disabled={rolePage === 1}
                    className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    <span>上一页</span>
                  </button>
                  <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                    <span className="font-bold text-indigo-600">{rolePage}</span>
                    <span className="text-slate-300">/</span>
                    <span>{totalRolePages}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setRolePage((prev) => Math.min(prev + 1, totalRolePages))}
                    disabled={rolePage === totalRolePages}
                    className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                  >
                    <span>下一页</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Role Assign and Edit Floating Centered Modal */}
          <AnimatePresence>
            {editingRole && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                {/* Backdrop Layer */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setEditingRole(null)}
                  className="absolute inset-0 bg-slate-900/45 backdrop-blur-xs"
                />

                {/* Modal Layout Box */}
                <motion.div
                  initial={{ scale: 0.96, y: 12, opacity: 0 }}
                  animate={{ scale: 1, y: 0, opacity: 1 }}
                  exit={{ scale: 0.96, y: 12, opacity: 0 }}
                  transition={{ type: 'spring', duration: 0.35, bounce: 0.1 }}
                  className="relative w-full max-w-4xl bg-white rounded-2xl border border-slate-200/80 shadow-2xl overflow-hidden z-10 flex flex-col max-h-[90vh]"
                >
                  {/* Header */}
                  <div className="px-6 py-4.5 border-b border-slate-100 flex justify-between items-center bg-slate-50/65">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <h3 className="text-sm font-bold text-slate-800">
                          {editingRole.isNew ? '创建全新系统角色' : `编辑角色 - [${editRoleName}] 权限及菜单管控分配`}
                        </h3>
                      </div>
                      <p className="text-[10px] text-slate-400 leading-normal">
                        维护该系统安全角色的元信息，并精准定制其受控的 38 项核心功能点与 11 个左侧导航菜单
                      </p>
                    </div>
                    <button
                      onClick={() => setEditingRole(null)}
                      className="p-1.5 hover:bg-slate-100 text-slate-400 hover:text-slate-600 rounded-lg transition-all cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Body Content Scrollable Area */}
                  <div className="p-6 space-y-6 overflow-y-auto max-h-[65vh] scrollbar-thin text-left">
                    {validationError && (
                      <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-red-650 text-xs font-semibold flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                        <span>{validationError}</span>
                      </div>
                    )}

                    {/* Metadata Section */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[10.5px] font-bold text-slate-700 block">角色名称 (name)</label>
                        <input
                          type="text"
                          value={editRoleName}
                          onChange={(e) => setEditRoleName(e.target.value)}
                          className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all font-semibold"
                          placeholder="例如：高级审查官"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10.5px] font-bold text-slate-700 block">
                          唯一英文代码标识 (code) 
                          {editRoleIsSystem && <span className="text-[9.5px] text-red-500 ml-1.5 font-normal">(内置系统角色，唯独不可更改该标识)</span>}
                        </label>
                        <input
                          type="text"
                          value={editRoleCode}
                          onChange={(e) => setEditRoleCode(e.target.value)}
                          disabled={editRoleIsSystem}
                          className={`w-full px-3.5 py-2.5 border rounded-xl text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all font-mono font-bold uppercase ${
                            editRoleIsSystem 
                              ? 'bg-slate-100 border-slate-200 text-slate-450 cursor-not-allowed select-all' 
                              : 'bg-slate-50 border-slate-200 focus:bg-white text-indigo-700'
                          }`}
                          placeholder="例如：SENIOR_REVIEWER"
                        />
                      </div>

                      <div className="md:col-span-2 space-y-1.5">
                        <label className="text-[10.5px] font-bold text-slate-700 block">职责要旨及描述说明 (description)</label>
                        <textarea
                          rows={2}
                          value={editRoleDesc}
                          onChange={(e) => setEditRoleDesc(e.target.value)}
                          className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all leading-relaxed font-light"
                          placeholder="简述该角色的工作内容与安全范围要求，对运营人员可见。"
                        />
                      </div>
                    </div>

                    {/* Menu Allocation Title Bar */}
                    <div className="border-t border-slate-100 pt-5 space-y-3">
                      <div className="flex justify-between items-center bg-slate-50/70 p-3 rounded-xl border border-slate-150">
                        <div className="space-y-0.5">
                          <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                            <Layers className="w-4 h-4 text-indigo-500" />
                            <span>1. 后台左侧系统菜单分配</span>
                          </label>
                          <p className="text-[10px] text-slate-400">勾选本角色在左侧 Sidebar 导航区中有权点击和访问的页面模块列表</p>
                        </div>
                        <div className="space-x-1.5">
                          <button
                            type="button"
                            onClick={() => setEditRoleMenus(allMenus.map(m => m.id))}
                            className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-indigo-600 shadow-3xs cursor-pointer"
                          >
                            集成全选
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditRoleMenus([])}
                            className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-slate-550 shadow-3xs cursor-pointer"
                          >
                            全部排空
                          </button>
                        </div>
                      </div>

                      {/* Menus Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
                        {allMenus.map((menu) => {
                          const isMenuSelected = editRoleMenus.includes(menu.id);
                          return (
                            <label
                              key={menu.id}
                              className={`flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer select-none ${
                                isMenuSelected
                                  ? 'bg-indigo-50/50 border-indigo-200 ring-1 ring-indigo-500/5'
                                  : 'bg-slate-50/30 border-slate-200/80 hover:bg-slate-50/50'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={isMenuSelected}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setEditRoleMenus([...editRoleMenus, menu.id]);
                                  } else {
                                    setEditRoleMenus(editRoleMenus.filter(mid => mid !== menu.id));
                                  }
                                }}
                                className="w-4 h-4 text-indigo-650 border-slate-300 focus:ring-indigo-500 rounded cursor-pointer"
                              />
                              <div className="flex items-center gap-2 font-medium">
                                <span className="p-1.5 bg-white border border-slate-200 rounded-lg shadow-3xs">
                                  {renderMenuIcon(menu.icon)}
                                </span>
                                <div className="space-y-0.5">
                                  <span className="text-xs font-bold text-slate-850 block">{menu.name}</span>
                                  <span className="text-[9.5px] font-mono text-slate-400 block">{menu.path}</span>
                                </div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>

                    {/* Permissions Section */}
                    <div className="border-t border-slate-100 pt-5 space-y-4">
                      <div className="flex justify-between items-center bg-slate-50/70 p-3 rounded-xl border border-slate-150">
                        <div className="space-y-0.5">
                          <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                            <ShieldCheck className="w-4 h-4 text-emerald-500" />
                            <span>2. 后台 38 项精细功能点准入权限分配</span>
                          </label>
                          <p className="text-[10px] text-slate-400">细化到每一个操作按钮、API触发动作的物理管控拦截，按功能主题划归</p>
                        </div>
                        <div className="space-x-1.5">
                          <button
                            type="button"
                            onClick={() => setEditRolePermissions(allPermissions.map(p => p.code))}
                            className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-emerald-600 shadow-3xs cursor-pointer"
                          >
                            赋予全功能 (38)
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditRolePermissions([])}
                            className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-slate-550 shadow-3xs cursor-pointer"
                          >
                            清除全部权限
                          </button>
                        </div>
                      </div>

                      {/* Group permissions by resource */}
                      <div className="space-y-4">
                        {Object.keys(resourceGroupNames).map((resKey) => {
                          const permissionsInGroup = allPermissions.filter(p => p.resource === resKey);
                          const isAllGroupSelected = permissionsInGroup.every(p => editRolePermissions.includes(p.code));
                          const isSomeGroupSelected = permissionsInGroup.some(p => editRolePermissions.includes(p.code)) && !isAllGroupSelected;

                          return (
                            <div key={resKey} className="border border-slate-150 rounded-xl overflow-hidden bg-slate-50/10">
                              <div className="px-4 py-2 bg-slate-50 flex justify-between items-center border-b border-slate-150">
                                <span className="text-xs font-bold text-slate-850 flex items-center gap-1.5">
                                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                                  <span>{resourceGroupNames[resKey]} ({resKey})</span>
                                </span>
                                <button
                                  type="button"
                                  onClick={() => {
                                    const groupCodes = permissionsInGroup.map(p => p.code);
                                    if (isAllGroupSelected) {
                                      // Remove all codes of this group
                                      setEditRolePermissions(editRolePermissions.filter(code => !groupCodes.includes(code)));
                                    } else {
                                      // Add all codes of this group (ensure no duplicates)
                                      const filtered = editRolePermissions.filter(code => !groupCodes.includes(code));
                                      setEditRolePermissions([...filtered, ...groupCodes]);
                                    }
                                  }}
                                  className="text-[10px] font-bold text-indigo-650 hover:text-indigo-800 bg-white hover:bg-indigo-50 border border-slate-200 px-2 py-0.5 rounded shadow-2xs transition-all cursor-pointer"
                                >
                                  {isAllGroupSelected ? '取消组内选择' : '全选组内'}
                                </button>
                              </div>

                              <div className="p-3.5 grid grid-cols-1 md:grid-cols-2 gap-3.5 bg-white">
                                {permissionsInGroup.map((p) => {
                                  const isChecked = editRolePermissions.includes(p.code);
                                  return (
                                    <label
                                      key={p.code}
                                      className={`p-2.5 rounded-xl border transition-all cursor-pointer select-none flex items-start gap-2.5 ${
                                        isChecked
                                          ? 'bg-emerald-50/30 border-emerald-250 ring-1 ring-emerald-500/5'
                                          : 'bg-white border-slate-150 hover:bg-slate-50/50'
                                      }`}
                                    >
                                      <input
                                        type="checkbox"
                                        checked={isChecked}
                                        onChange={(e) => {
                                          if (e.target.checked) {
                                            setEditRolePermissions([...editRolePermissions, p.code]);
                                          } else {
                                            setEditRolePermissions(editRolePermissions.filter(code => code !== p.code));
                                          }
                                        }}
                                        className="mt-0.5 w-4 h-4 text-emerald-600 border-slate-300 focus:ring-emerald-500 rounded cursor-pointer"
                                      />
                                      <div className="space-y-0.5 text-xs text-left">
                                        <div className="flex items-center gap-1.5 font-bold">
                                          <span className="text-slate-800">{p.name}</span>
                                          <span className="text-[8.5px] font-mono text-indigo-700 bg-indigo-50 px-1 py-0.2 rounded font-semibold">
                                            {p.code}
                                          </span>
                                        </div>
                                        <p className="text-[10.5px] text-slate-450 font-light leading-normal">
                                          {p.description}
                                        </p>
                                      </div>
                                    </label>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Footer actions */}
                  <div className="px-6 py-4.5 border-t border-slate-100 bg-slate-50/30 flex justify-end gap-3 z-20">
                    <button
                      onClick={() => setEditingRole(null)}
                      className="px-4 py-2 bg-white hover:bg-slate-50 active:bg-slate-100 border border-slate-200 text-slate-650 text-xs font-semibold rounded-xl transition-all cursor-pointer"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSaveRole}
                      className="px-5 py-2.5 bg-[#0b0c16] text-[#93c5fd] hover:bg-[#121424] active:bg-[#06070c] border border-[#2b3558] text-xs font-bold rounded-xl transition-all shadow-xs cursor-pointer"
                    >
                      保存权限配置
                    </button>
                  </div>
                </motion.div>
              </div>
            )}
          </AnimatePresence>
        </div>
      ) : null}
    </div>
  );
}
