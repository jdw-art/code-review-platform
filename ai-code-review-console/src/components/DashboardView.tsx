/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { motion } from 'motion/react';
import {
  ShieldCheck,
  Compass,
  LayoutGrid,
  TrendingUp,
  FileCheck2,
  FolderOpen,
  ArrowRight,
  GitPullRequest,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  Sparkles,
  BarChart3,
  Users2,
  GitCommit,
  LineChart as LucideLineChart,
  Diff,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { DashboardStats, ProjectItem, ReviewRecord, ModelConfig } from '../types';

interface DashboardViewProps {
  username: string;
  stats: DashboardStats;
  recentReviews: ReviewRecord[];
  allProjects: ProjectItem[];
  modelConfigs: ModelConfig[];
  onNavigateTab: (tab: any) => void;
  onToggleProject: (id: string) => void;
}

export default function DashboardView({
  username,
  stats,
  recentReviews,
  allProjects,
  modelConfigs,
  onNavigateTab,
  onToggleProject,
}: DashboardViewProps) {
  // Compute real-time values from current list state (makes the UI live)
  const totalProjects = allProjects.length;
  const activeProjectsCount = allProjects.filter((p) => p.enabled).length;
  const activeModel = modelConfigs.find((m) => m.isActive)?.name || 'Gemini 2.5 Pro';

  // Base persistent high-fidelity datasets to prevent empty initial graphs
  const baseProjectStats: Record<string, { commits: number; totalScore: number; added: number; deleted: number }> = {
    'ai-code-reviewer': { commits: 15, totalScore: 1320, added: 4120, deleted: 1150 },
    'agent-compiler-core': { commits: 12, totalScore: 912, added: 2750, deleted: 820 },
    'notification-robot-bridge': { commits: 9, totalScore: 828, added: 1900, deleted: 380 },
    'webapp-frontend-console': { commits: 11, totalScore: 715, added: 5500, deleted: 2980 },
    'access-context-rbac': { commits: 6, totalScore: 495, added: 1180, deleted: 310 },
    'local-postgres-syncer': { commits: 4, totalScore: 232, added: 820, deleted: 610 },
  };

  const baseMemberStats: Record<string, { commits: number; totalScore: number; added: number; deleted: number }> = {
    'jdw-art': { commits: 19, totalScore: 1638, added: 7050, deleted: 2680 },
    'admin': { commits: 14, totalScore: 1183, added: 3010, deleted: 1050 },
    'system-agent': { commits: 12, totalScore: 1008, added: 2410, deleted: 1210 },
    'developer': { commits: 8, totalScore: 632, added: 1750, deleted: 950 },
    'sarah-qa': { commits: 4, totalScore: 364, added: 1150, deleted: 280 },
  };

  // Dynamically compound with live trigger state reviews (fully real-time reactive)
  recentReviews.forEach((rev) => {
    const projName = rev.projectName || 'ai-code-reviewer';
    const matchKey = Object.keys(baseProjectStats).find((k) => k.toLowerCase() === projName.toLowerCase()) || projName;
    if (!baseProjectStats[matchKey]) {
      baseProjectStats[matchKey] = { commits: 0, totalScore: 0, added: 0, deleted: 0 };
    }
    baseProjectStats[matchKey].commits += 1;
    baseProjectStats[matchKey].totalScore += rev.score;
    // Generate nice simulated code diff ratios based on scores
    baseProjectStats[matchKey].added += Math.round(rev.score * 4.2);
    baseProjectStats[matchKey].deleted += Math.round(rev.score * 1.5);

    const committer = rev.committer || 'jdw-art';
    const matchMember = Object.keys(baseMemberStats).find((k) => k.toLowerCase() === committer.toLowerCase()) || committer;
    if (!baseMemberStats[matchMember]) {
      baseMemberStats[matchMember] = { commits: 0, totalScore: 0, added: 0, deleted: 0 };
    }
    baseMemberStats[matchMember].commits += 1;
    baseMemberStats[matchMember].totalScore += rev.score;
    baseMemberStats[matchMember].added += Math.round(rev.score * 4.2);
    baseMemberStats[matchMember].deleted += Math.round(rev.score * 1.5);
  });

  const projectChartData = Object.entries(baseProjectStats).map(([name, val]) => ({
    name,
    commits: val.commits,
    avgScore: parseFloat((val.totalScore / Math.max(1, val.commits)).toFixed(1)),
    added: val.added,
    deleted: val.deleted,
  }));

  const memberChartData = Object.entries(baseMemberStats).map(([name, val]) => ({
    name: name === 'jdw-art' ? 'jdw-art' : name,
    commits: val.commits,
    avgScore: parseFloat((val.totalScore / Math.max(1, val.commits)).toFixed(1)),
    added: val.added,
    deleted: val.deleted,
  }));

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* 1. Welcome Hero Banner */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-linear-to-r from-indigo-50/40 via-[#f8fafc] to-slate-100/70 text-slate-800 rounded-3xl p-8 shadow-xs border border-slate-200/80 relative overflow-hidden group"
      >
        <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-550/5 rounded-full blur-3xl pointer-events-none group-hover:bg-indigo-500/10 transition-all duration-1000" />
        <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold tracking-widest text-indigo-700 bg-indigo-100/70 px-2.5 py-0.5 rounded-sm border border-indigo-200/30 font-mono">
              DASHBOARD
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-505" />
            <span className="text-xs text-slate-500 font-mono font-medium">活动模型: {activeModel}</span>
          </div>

          <div className="space-y-2">
            <h2 className="text-2.5xl font-extrabold text-slate-900 tracking-tight">
              {username || 'jdw-art'}，欢迎进入代码复审控制中心
            </h2>
            <p className="text-slate-500 text-xs sm:text-xs font-light max-w-4xl leading-relaxed">
              智能代码审查控制台已就绪。系统正持续监听各接入代码仓库的 Pull Request 与变更状态，结合多语言大型模型开展 AST 结构、耦合度冗余、潜在安全漏洞等多维度实时复审，辅助团队打造高质量且安全的整洁代码架构。
            </p>
          </div>

          <div className="pt-2 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigateTab('projects')}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold cursor-pointer transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98]"
            >
              <span>仓库项目配置</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onNavigateTab('models')}
              className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold cursor-pointer transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98]"
            >
              <span>切换审核模型</span>
            </button>
          </div>
        </div>
      </motion.div>

      {/* 2. KPIs Stat Matrix  */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* KPI 1 */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">项目总数</span>
            <FolderOpen className="w-4.5 h-4.5 text-indigo-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-slate-950 font-mono tracking-tight">
              {totalProjects}
            </div>
            <p className="text-xs text-slate-450">
              纳入后台管理的仓库代码项目总数。
            </p>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">启用项目</span>
            <FileCheck2 className="w-4.5 h-4.5 text-emerald-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-[#000000] font-mono tracking-tight flex items-baseline gap-2">
              <span>{activeProjectsCount}</span>
              <span className="text-xs text-slate-400 font-normal">/ {totalProjects}</span>
            </div>
            <p className="text-xs text-slate-450">
              当前处于启用监控审查状态的项目。
            </p>
          </div>
        </div>

        {/* KPI 3 */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">审查记录</span>
            <GitPullRequest className="w-4.5 h-4.5 text-purple-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-slate-950 font-mono tracking-tight">
              {stats.reviewCount}
            </div>
            <p className="text-xs text-slate-450">
              系统累计写入并打分的审查事件总和。
            </p>
          </div>
        </div>

        {/* KPI 4 */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">平均评分</span>
            <TrendingUp className="w-4.5 h-4.5 text-orange-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-indigo-600 font-mono tracking-tight">
              {stats.averageScore.toFixed(1)}
            </div>
            <p className="text-xs text-slate-450">
              全量项目已评分审查记录的总体均分。
            </p>
          </div>
        </div>
      </div>

      {/* 3. Realtime Logs/Monitor Widgets Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Side: Core Interactive Event Monitor (Pull Request Review Log) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <GitPullRequest className="w-4.5 h-4.5 text-indigo-500" />
                <span>实时审查流水线监视器</span>
              </h3>
              <p className="text-xs text-slate-400">
                本工作区自动关联触发的 PR/MR 审查事件日志。可模拟即时拦截重审。
              </p>
            </div>
            <button
              onClick={() => onNavigateTab('records')}
              className="text-xs font-semibold text-indigo-600 hover:underline cursor-pointer flex items-center gap-1"
            >
              <span>查看全部记录 ({stats.reviewCount})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {recentReviews.slice(0, 4).map((record) => {
              const scoreColor =
                record.score >= 90
                  ? 'text-emerald-600 bg-emerald-50 border-emerald-100'
                  : record.score >= 75
                  ? 'text-indigo-600 bg-indigo-50 border-indigo-100'
                  : record.score >= 60
                  ? 'text-amber-600 bg-amber-50 border-amber-100'
                  : 'text-red-600 bg-red-50 border-red-100';

              const StatusIcon =
                record.status === 'excellent'
                  ? CheckCircle
                  : record.status === 'pass'
                  ? CheckCircle
                  : record.status === 'warning'
                  ? AlertTriangle
                  : XCircle;

              const statusColor =
                record.status === 'excellent'
                  ? 'text-emerald-500'
                  : record.status === 'pass'
                  ? 'text-indigo-500'
                  : record.status === 'warning'
                  ? 'text-amber-500'
                  : 'text-red-500';

              return (
                <div
                  key={record.id}
                  className="py-4 first:pt-0 last:pb-0 flex items-start gap-4 hover:bg-slate-50/40 px-2 rounded-xl transition-colors"
                >
                  <div className={`p-2 rounded-lg bg-slate-50 text-slate-400 mt-0.5`}>
                    <StatusIcon className={`w-4.5 h-4.5 ${statusColor}`} />
                  </div>

                  <div className="grow space-y-1.5">
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <h4 className="text-xs font-bold text-slate-800 leading-tight">
                          {record.projectName}
                        </h4>
                        <p className="text-xs text-slate-600 font-medium font-sans">
                          {record.prTitle}
                        </p>
                      </div>
                      <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded-sm border ${scoreColor}`}>
                        {record.score}分
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400 font-light">
                      <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded-xs text-slate-600">
                        {record.branch} @ {record.commitHash}
                      </span>
                      <span>•</span>
                      <span>提交者: {record.committer}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {record.timestamp}
                      </span>
                    </div>

                    <p className="text-xs text-slate-500 italic bg-slate-50/50 p-2 rounded-lg border border-slate-100">
                      AI 审查摘要: {record.summary}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Side: Quick Action and System Context Explanations */}
        <div className="space-y-6">
          {/* Quick Active Model Widgets */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>当前智算节点</span>
            </h3>

            <div className="space-y-2">
              {modelConfigs.map((model) => (
                <div
                  key={model.id}
                  className={`p-3 rounded-xl border transition-all flex items-center justify-between ${
                    model.isActive
                      ? 'bg-indigo-500/5 border-indigo-200 text-indigo-950 font-medium'
                      : 'bg-white border-slate-200 text-slate-500'
                  }`}
                >
                  <div>
                    <h4 className="text-xs font-bold">{model.name}</h4>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {model.provider} API • Temp {model.temperature}
                    </span>
                  </div>

                  {model.isActive ? (
                    <span className="text-[10px] bg-indigo-600 text-white font-bold py-0.5 px-2 rounded-full">
                      运行中
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-400 bg-slate-100 py-0.5 px-2 rounded-full">
                      备用
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Quick Code repo summaries */}
          <div className="bg-slate-50/70 border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-4.5 h-4.5 text-indigo-600" />
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono">
                仓库健康审查极
              </h3>
            </div>

            <div className="space-y-2">
              {allProjects.slice(0, 3).map((p) => (
                <div key={p.id} className="flex justify-between items-center text-xs">
                  <span className="text-slate-700 font-semibold truncate max-w-[120px]">{p.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-500 font-mono">均分: {p.scoreAverage}</span>
                    <span
                      onClick={() => onToggleProject(p.id)}
                      className={`w-2.5 h-2.5 rounded-full cursor-pointer ${
                        p.enabled ? 'bg-emerald-500' : 'bg-slate-350'
                      }`}
                      title={p.enabled ? '已启用监控 - 点击切换' : '已暂停监控 - 点击切换'}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3.5 Quantitative Performance Analytics Center */}
      <div className="space-y-6 pt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/60 pb-4">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-500" />
              <span>研发效能可视化度量中心</span>
            </h3>
            <p className="text-xs text-slate-400">
              基于 AST 与 LLM 审查日志，全自动统计项目、成员的提交频次、代码分值及代码变更行数。
            </p>
          </div>
          <div className="flex items-center gap-1 bg-slate-50 px-2.5 py-1 rounded-lg text-[10px] font-mono text-slate-500 border border-slate-200/40">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse inline-block" />
            <span>METRICS INTERACTIVE ACTIVE</span>
          </div>
        </div>

        {/* Row 1: Commits Counts (Project Commits & Member Commits) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Chart 1: Project Commits Count */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <GitCommit className="w-4 h-4 text-indigo-500" />
                <span>各项目代码提交频次</span>
              </h4>
              <span className="text-[10px] text-slate-400 font-mono">单位: 次</span>
            </div>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={projectChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', fontSize: '11px' }}
                    cursor={{ fill: 'rgba(99, 102, 241, 0.04)' }}
                  />
                  <Bar dataKey="commits" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={22} name="提交次数" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Member Commits Count */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Users2 className="w-4 h-4 text-emerald-500" />
                <span>团队成员提交热度</span>
              </h4>
              <span className="text-[10px] text-slate-400 font-mono">单位: 次</span>
            </div>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={memberChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', fontSize: '11px' }}
                    cursor={{ fill: 'rgba(16, 185, 129, 0.04)' }}
                  />
                  <Bar dataKey="commits" fill="#10b981" radius={[4, 4, 0, 0]} barSize={22} name="提交次数" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Row 2: Average Scores (Project Avg Score vs. Member Avg Score) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Chart 3: Project Average Score */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-violet-500" />
                <span>各项目代码质量平均得分趋势</span>
              </h4>
              <span className="text-[10px] text-slate-400 font-mono">满分: 100</span>
            </div>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={projectChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} domain={[40, 100]} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', fontSize: '11px' }}
                  />
                  <Line type="monotone" dataKey="avgScore" stroke="#8b5cf6" strokeWidth={2.5} dot={{ r: 4, strokeWidth: 2 }} name="平均得分" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 4: Member Average Score */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <LucideLineChart className="w-4 h-4 text-pink-500" />
                <span>成员代码质量评分指数</span>
              </h4>
              <span className="text-[10px] text-slate-400 font-mono">满分: 100</span>
            </div>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={memberChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} domain={[40, 100]} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', fontSize: '11px' }}
                    cursor={{ fill: 'rgba(236, 72, 153, 0.04)' }}
                  />
                  <Bar dataKey="avgScore" fill="#ec4899" radius={[4, 4, 0, 0]} barSize={22} name="均分" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Row 3: Code Changes Lines (Project Added/Deleted vs. Member Added/Deleted) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Chart 5: Project lines added vs. deleted */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Diff className="w-4 h-4 text-blue-500" />
                <span>项目代码变更规模控制 (增加 / 删除)</span>
              </h4>
              <span className="text-[10px] text-slate-400 font-mono">单位: 行</span>
            </div>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={projectChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', fontSize: '11px' }}
                  />
                  <Legend verticalAlign="top" height={32} iconType="circle" iconSize={6} wrapperStyle={{ fontSize: '10px' }} />
                  <Bar dataKey="added" fill="#10b981" radius={[3, 3, 0, 0]} name="增加行数" />
                  <Bar dataKey="deleted" fill="#f43f5e" radius={[3, 3, 0, 0]} name="删除行数" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 6: Member lines added vs. deleted */}
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Diff className="w-4 h-4 text-teal-500" />
                <span>成员代码变更差异度量 (增加 / 删除)</span>
              </h4>
              <span className="text-[10px] text-slate-400 font-mono">单位: 行</span>
            </div>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={memberChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', fontSize: '11px' }}
                  />
                  <Legend verticalAlign="top" height={32} iconType="circle" iconSize={6} wrapperStyle={{ fontSize: '10px' }} />
                  <Bar dataKey="added" fill="#14b8a6" radius={[3, 3, 0, 0]} name="增加行数" />
                  <Bar dataKey="deleted" fill="#f43f5e" radius={[3, 3, 0, 0]} name="删除行数" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Three Feature Card Modules (from screenshot page bottom) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        {/* Module 1 */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,0,0,0.015)] transition-all">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl bg-slate-50 text-slate-800 flex items-center justify-center border border-slate-200/60">
              <ShieldCheck className="w-4.5 h-4.5 text-indigo-600" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-slate-900">静态安全与合规扫描 (AST Scan)</h3>
              <p className="text-[11px] text-slate-400 font-light leading-relaxed">
                全自动解析代码抽象语法树（AST），检测潜在的内存泄露、高风险 API 滥用以及不合规的硬编码保密凭证。
              </p>
            </div>
          </div>
          <span className="text-[9px] text-slate-500 font-bold tracking-wider font-mono uppercase bg-slate-50 mt-4 px-2.5 py-1 rounded-md border border-slate-200/40 w-fit">
            AST_COMPLIANCE_STANDARDS
          </span>
        </div>

        {/* Module 2 */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,0,0,0.015)] transition-all">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl bg-slate-50 text-slate-800 flex items-center justify-center border border-slate-200/60">
              <Compass className="w-4.5 h-4.5 text-indigo-600" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-slate-900">轻量级 RBAC 矩阵控制</h3>
              <p className="text-[11px] text-slate-400 font-light leading-relaxed">
                由统一的访问权限树（access-context）驱动侧边栏。精准分配按钮操作与只读层级，实现零死角的细粒度权限托管。
              </p>
            </div>
          </div>
          <span className="text-[9px] text-slate-500 font-bold tracking-wider font-mono uppercase bg-slate-50 mt-4 px-2.5 py-1 rounded-md border border-slate-200/40 w-fit">
            RBAC_ACCESS_SECURED
          </span>
        </div>

        {/* Module 3 */}
        <div className="bg-white rounded-2xl border border-slate-200/60 p-6 flex flex-col justify-between hover:shadow-[0_4px_20px_rgba(0,0,0,0.015)] transition-all">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl bg-slate-50 text-slate-800 flex items-center justify-center border border-slate-200/60">
              <LayoutGrid className="w-4.5 h-4.5 text-indigo-600" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-slate-900">多模型 Agent 诊断通道</h3>
              <p className="text-[11px] text-slate-400 font-light leading-relaxed">
                全量接入 Gemini 及各类智算节点。当有代码提交事件产生，多智能体联动诊断可瞬时完成全仓库深度扫描与分析。
              </p>
            </div>
          </div>
          <span className="text-[9px] text-slate-500 font-bold tracking-wider font-mono uppercase bg-slate-50 mt-4 px-2.5 py-1 rounded-md border border-slate-200/40 w-fit">
            AI_AGENT_DIAGNOSTICS
          </span>
        </div>
      </div>
    </div>
  );
}
