import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle,
  Clock,
  Compass,
  Diff,
  FileCheck2,
  FolderOpen,
  GitCommit,
  GitPullRequest,
  LayoutGrid,
  LineChart as LucideLineChart,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users2,
  XCircle,
} from "lucide-react";
import { motion } from "motion/react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useNavigate } from "react-router-dom";

import { getDashboardOverview } from "../../features/dashboard/api";
import {
  toConsoleDashboardOverview,
  type ConsoleDashboardOverview,
} from "../../features/dashboard/serializers";
import type {
  DashboardRecentReviewItem,
} from "../../lib/api/types";
import { useAuth } from "../../lib/auth/auth-context";

function formatScore(score: number | null) {
  return score === null ? "-" : score.toFixed(1);
}

function readErrorMessage(error: unknown) {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "请稍后重试。";
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "暂无记录";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

function scoreBadgeClass(score: number | null) {
  if (score === null) {
    return "border-slate-200 bg-slate-50 text-slate-500";
  }
  if (score >= 90) {
    return "border-emerald-100 bg-emerald-50 text-emerald-600";
  }
  if (score >= 75) {
    return "border-indigo-100 bg-indigo-50 text-indigo-600";
  }
  if (score >= 60) {
    return "border-amber-100 bg-amber-50 text-amber-600";
  }
  return "border-rose-100 bg-rose-50 text-rose-600";
}

function reviewStatusIcon(review: DashboardRecentReviewItem) {
  if (review.review_status === "reviewed" && (review.score ?? 0) >= 90) {
    return {
      Icon: CheckCircle,
      colorClassName: "text-emerald-500",
    };
  }
  if (review.review_status === "reviewed") {
    return {
      Icon: CheckCircle,
      colorClassName: "text-indigo-500",
    };
  }
  if (review.review_status === "pending") {
    return {
      Icon: AlertTriangle,
      colorClassName: "text-amber-500",
    };
  }
  return {
    Icon: XCircle,
    colorClassName: "text-rose-500",
  };
}

/**
 * 仪表盘页面以原型为唯一视觉基准，保留真实后端数据并将其映射到高保真控制台布局中。
 */
export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const displayName = user?.username?.trim() || user?.nickname?.trim() || "jdw-art";
  const { data, error, isError, isPending, refetch } = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => getDashboardOverview(),
    select: toConsoleDashboardOverview,
  });

  if (isPending && data === undefined) {
    return (
      <section className="space-y-8">
        <div className="rounded-[2rem] border border-slate-200/80 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">
            Dashboard
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">
            {displayName}，欢迎进入代码复审控制中心
          </h1>
          <p className="mt-3 text-sm text-slate-600">正在加载仪表盘概览...</p>
        </div>
      </section>
    );
  }

  if (isError && data === undefined) {
    return (
      <section className="space-y-8">
        <div className="rounded-[2rem] border border-rose-200 bg-rose-50/70 p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-rose-700">
            Dashboard
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">
            仪表盘概览加载失败
          </h1>
          <p className="mt-3 text-sm text-slate-700">{readErrorMessage(error)}</p>
          <button
            type="button"
            onClick={() => void refetch()}
            className="mt-5 rounded-2xl border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100"
          >
            重新加载
          </button>
        </div>
      </section>
    );
  }

  const overview = data as ConsoleDashboardOverview;
  const projectChartData = overview.projectChart.map((item) => ({
    name: item.name,
    commits: item.commits,
    avgScore: item.avg_score === null ? 0 : Number(item.avg_score.toFixed(1)),
    added: item.additions,
    deleted: item.deletions,
  }));
  const memberChartData = overview.memberChart.map((item) => ({
    name: item.name,
    commits: item.commits,
    avgScore: item.avg_score === null ? 0 : Number(item.avg_score.toFixed(1)),
    added: item.additions,
    deleted: item.deletions,
  }));

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        data-dashboard-hero
        className="bg-gradient-to-r from-indigo-50/40 via-[#f8fafc] to-slate-100/70 text-slate-800 rounded-3xl p-8 shadow-xs border border-slate-200/80 relative overflow-hidden group"
      >
        <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-550/5 rounded-full blur-3xl pointer-events-none group-hover:bg-indigo-500/10 transition-all duration-1000" />
        <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold tracking-widest text-indigo-700 bg-indigo-100/70 px-2.5 py-0.5 rounded-sm border border-indigo-200/30 font-mono">
              DASHBOARD
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-505" />
            <span className="text-xs text-slate-500 font-mono font-medium">
              活动模型: {overview.activeModelName ?? "未配置默认模型"}
            </span>
          </div>

          <div className="space-y-2">
            <h2 className="text-2.5xl font-extrabold text-slate-900 tracking-tight">
              {displayName}，欢迎进入代码复审控制中心
            </h2>
            <p className="text-slate-500 text-xs sm:text-xs font-light max-w-4xl leading-relaxed">
              智能代码审查控制台已就绪。系统正持续监听各接入代码仓库的 Pull Request 与变更状态，结合多语言大型模型开展 AST 结构、耦合度冗余、潜在安全漏洞等多维度实时复审，辅助团队打造高质量且安全的整洁代码架构。
            </p>
          </div>

          <div className="pt-2 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => navigate("/projects")}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold cursor-pointer transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98]"
            >
              <span>仓库项目配置</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => navigate("/models")}
              className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold cursor-pointer transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98]"
            >
              <span>切换审核模型</span>
            </button>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div data-dashboard-kpi-card className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">项目总数</span>
            <FolderOpen className="w-4.5 h-4.5 text-indigo-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-slate-950 font-mono tracking-tight">
              {overview.totalProjects}
            </div>
            <p className="text-xs text-slate-450">纳入后台管理的仓库代码项目总数。</p>
          </div>
        </div>

        <div data-dashboard-kpi-card className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">启用项目</span>
            <FileCheck2 className="w-4.5 h-4.5 text-emerald-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-[#000000] font-mono tracking-tight flex items-baseline gap-2">
              <span>{overview.activeProjects}</span>
              <span className="text-xs text-slate-400 font-normal">/ {overview.totalProjects}</span>
            </div>
            <p className="text-xs text-slate-450">当前处于启用监控审查状态的项目。</p>
          </div>
        </div>

        <div data-dashboard-kpi-card className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">审查记录</span>
            <GitPullRequest className="w-4.5 h-4.5 text-purple-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-slate-950 font-mono tracking-tight">
              {overview.totalReviewRecords}
            </div>
            <p className="text-xs text-slate-450">系统累计写入并打分的审查事件总和。</p>
          </div>
        </div>

        <div data-dashboard-kpi-card className="bg-white rounded-2xl p-6 border border-slate-200/70 shadow-xs hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-3 text-slate-400">
            <span className="text-xs font-semibold tracking-wide uppercase">平均评分</span>
            <TrendingUp className="w-4.5 h-4.5 text-orange-500" />
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-extrabold text-indigo-600 font-mono tracking-tight">
              {formatScore(overview.averageScore)}
            </div>
            <p className="text-xs text-slate-450">全量项目已评分审查记录的总体均分。</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
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
              type="button"
              onClick={() => navigate("/review-records")}
              className="text-xs font-semibold text-indigo-600 hover:underline cursor-pointer flex items-center gap-1"
            >
              <span>查看全部记录 ({overview.totalReviewRecords})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {overview.recentReviews.length > 0 ? (
              overview.recentReviews.slice(0, 4).map((review) => {
                const { Icon, colorClassName } = reviewStatusIcon(review);

                return (
                  <div
                    key={review.id}
                    className="py-4 first:pt-0 last:pb-0 flex items-start gap-4 hover:bg-slate-50/40 px-2 rounded-xl transition-colors"
                  >
                    <div className="p-2 rounded-lg bg-slate-50 text-slate-400 mt-0.5">
                      <Icon className={`w-4.5 h-4.5 ${colorClassName}`} />
                    </div>

                    <div className="grow space-y-1.5">
                      <div className="flex justify-between items-start gap-2">
                        <div>
                          <h4 className="text-xs font-bold text-slate-800 leading-tight">
                            {review.project_name}
                          </h4>
                          <p className="text-xs text-slate-600 font-medium font-sans">
                            {review.title ?? "未命名审查记录"}
                          </p>
                        </div>
                        <span
                          className={`text-xs font-mono font-bold px-2 py-0.5 rounded-sm border ${scoreBadgeClass(review.score)}`}
                        >
                          {review.score === null ? "-" : `${review.score}分`}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 font-light">
                        <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded-xs text-slate-600">
                          {review.branch ?? "unknown"} @ {review.commit_hash ?? "no-hash"}
                        </span>
                        <span>•</span>
                        <span>提交者: {review.committer ?? "unknown"}</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTimestamp(review.created_at)}
                        </span>
                      </div>

                      <p className="text-xs text-slate-500 italic bg-slate-50/50 p-2 rounded-lg border border-slate-100">
                        AI 审查摘要: {review.summary ?? "暂无摘要。"}
                      </p>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="rounded-xl bg-slate-50 px-4 py-6 text-sm text-slate-500">
                暂无最近审查记录。
              </p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>当前智算节点</span>
            </h3>

            <div className="space-y-2">
              {overview.models.length > 0 ? (
                overview.models.map((model) => (
                  <div
                    key={model.id}
                    className={`p-3 rounded-xl border transition-all flex items-center justify-between ${
                      model.is_active
                        ? "bg-indigo-500/5 border-indigo-200 text-indigo-950 font-medium"
                        : "bg-white border-slate-200 text-slate-500"
                    }`}
                  >
                    <div>
                      <h4 className="text-xs font-bold">{model.name}</h4>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {model.provider} API
                        {model.temperature === null ? "" : ` • Temp ${model.temperature}`}
                      </span>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                      {model.is_active ? (
                        <span className="text-[10px] bg-indigo-600 text-white font-bold py-0.5 px-2 rounded-full">
                          运行中
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400 bg-slate-100 py-0.5 px-2 rounded-full">
                          备用
                        </span>
                      )}
                      {model.is_default ? (
                        <span className="text-[10px] font-semibold text-indigo-600">默认模型</span>
                      ) : null}
                    </div>
                  </div>
                ))
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-5 text-sm text-slate-500">暂无模型配置。</p>
              )}
            </div>
          </div>

          <div className="bg-slate-50/70 border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-4.5 h-4.5 text-indigo-600" />
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono">
                仓库健康审查极
              </h3>
            </div>

            <div className="space-y-2">
              {overview.repoHealth.length > 0 ? (
                overview.repoHealth.slice(0, 3).map((project) => (
                  <div key={project.project_id} className="flex justify-between items-center text-xs">
                    <span className="text-slate-700 font-semibold truncate max-w-[120px]">{project.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-slate-500 font-mono">均分: {formatScore(project.average_score)}</span>
                      <span
                        title={project.is_active ? "已启用监控" : "已暂停监控"}
                        className={`w-2.5 h-2.5 rounded-full ${
                          project.is_active ? "bg-emerald-500" : "bg-slate-350"
                        }`}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <p className="rounded-xl bg-white px-4 py-5 text-sm text-slate-500">暂无仓库健康数据。</p>
              )}
            </div>
          </div>
        </div>
      </div>

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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <GitCommit className="w-4 h-4 text-indigo-500" />
                <span>各项目代码提交频次</span>
              </h4>
              <span className="font-mono text-[10px] text-slate-400">单位: 次</span>
            </div>
            <div className="w-full h-64">
              {projectChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={projectChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: "11px" }}
                      cursor={{ fill: "rgba(99, 102, 241, 0.04)" }}
                    />
                    <Bar dataKey="commits" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={22} name="提交次数" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">暂无项目提交频次数据。</p>
              )}
            </div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Users2 className="w-4 h-4 text-emerald-500" />
                <span>团队成员提交热度</span>
              </h4>
              <span className="font-mono text-[10px] text-slate-400">单位: 次</span>
            </div>
            <div className="w-full h-64">
              {memberChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={memberChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: "11px" }}
                      cursor={{ fill: "rgba(16, 185, 129, 0.04)" }}
                    />
                    <Bar dataKey="commits" fill="#10b981" radius={[4, 4, 0, 0]} barSize={22} name="提交次数" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">暂无成员提交热度数据。</p>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-violet-500" />
                <span>各项目代码质量平均得分趋势</span>
              </h4>
              <span className="font-mono text-[10px] text-slate-400">满分: 100</span>
            </div>
            <div className="w-full h-64">
              {projectChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={projectChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} domain={[40, 100]} />
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: "11px" }}
                    />
                    <Line type="monotone" dataKey="avgScore" stroke="#8b5cf6" strokeWidth={2.5} dot={{ r: 4, strokeWidth: 2 }} name="平均得分" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">暂无项目质量评分趋势数据。</p>
              )}
            </div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <LucideLineChart className="w-4 h-4 text-pink-500" />
                <span>成员代码质量评分指数</span>
              </h4>
              <span className="font-mono text-[10px] text-slate-400">满分: 100</span>
            </div>
            <div className="w-full h-64">
              {memberChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={memberChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} domain={[40, 100]} />
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: "11px" }}
                      cursor={{ fill: "rgba(236, 72, 153, 0.04)" }}
                    />
                    <Bar dataKey="avgScore" fill="#ec4899" radius={[4, 4, 0, 0]} barSize={22} name="均分" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">暂无成员质量评分数据。</p>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Diff className="w-4 h-4 text-blue-500" />
                <span>项目代码变更规模控制 (增加 / 删除)</span>
              </h4>
              <span className="font-mono text-[10px] text-slate-400">单位: 行</span>
            </div>
            <div className="w-full h-64">
              {projectChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={projectChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: "11px" }}
                    />
                    <Legend verticalAlign="top" height={32} iconType="circle" iconSize={6} wrapperStyle={{ fontSize: "10px" }} />
                    <Bar dataKey="added" fill="#10b981" radius={[3, 3, 0, 0]} name="增加行数" />
                    <Bar dataKey="deleted" fill="#f43f5e" radius={[3, 3, 0, 0]} name="删除行数" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">暂无项目代码变更规模数据。</p>
              )}
            </div>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200/60 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Diff className="w-4 h-4 text-teal-500" />
                <span>成员代码变更差异度量 (增加 / 删除)</span>
              </h4>
              <span className="font-mono text-[10px] text-slate-400">单位: 行</span>
            </div>
            <div className="w-full h-64">
              {memberChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={memberChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={9} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: "11px" }}
                    />
                    <Legend verticalAlign="top" height={32} iconType="circle" iconSize={6} wrapperStyle={{ fontSize: "10px" }} />
                    <Bar dataKey="added" fill="#14b8a6" radius={[3, 3, 0, 0]} name="增加行数" />
                    <Bar dataKey="deleted" fill="#f43f5e" radius={[3, 3, 0, 0]} name="删除行数" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">暂无成员代码变更规模数据。</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <div className="bg-white border border-slate-200/60 rounded-2xl p-6 transition-all hover:shadow-[0_4px_20px_rgba(0,0,0,0.015)] flex flex-col justify-between">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl border border-slate-200/60 bg-slate-50 flex items-center justify-center text-slate-800">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-slate-900">静态安全与合规扫描 (AST Scan)</h3>
              <p className="text-[11px] text-slate-400 leading-relaxed font-light">
                全自动解析代码抽象语法树（AST），检测潜在的内存泄露、高风险 API 滥用以及不合规的硬编码保密凭证。
              </p>
            </div>
          </div>
          <span className="mt-4 w-fit px-2.5 py-1 rounded-md border border-slate-200/40 bg-slate-50 text-[9px] font-mono font-bold tracking-wider uppercase text-slate-500">
            AST_COMPLIANCE_STANDARDS
          </span>
        </div>

        <div className="bg-white border border-slate-200/60 rounded-2xl p-6 transition-all hover:shadow-[0_4px_20px_rgba(0,0,0,0.015)] flex flex-col justify-between">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl border border-slate-200/60 bg-slate-50 flex items-center justify-center text-slate-800">
              <Compass className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-slate-900">轻量级 RBAC 矩阵控制</h3>
              <p className="text-[11px] text-slate-400 leading-relaxed font-light">
                由统一的访问权限树（access-context）驱动侧边栏。精准分配按钮操作与只读层级，实现零死角的细粒度权限托管。
              </p>
            </div>
          </div>
          <span className="mt-4 w-fit px-2.5 py-1 rounded-md border border-slate-200/40 bg-slate-50 text-[9px] font-mono font-bold tracking-wider uppercase text-slate-500">
            RBAC_ACCESS_SECURED
          </span>
        </div>

        <div className="bg-white border border-slate-200/60 rounded-2xl p-6 transition-all hover:shadow-[0_4px_20px_rgba(0,0,0,0.015)] flex flex-col justify-between">
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-xl border border-slate-200/60 bg-slate-50 flex items-center justify-center text-slate-800">
              <LayoutGrid className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-slate-900">多模型 Agent 诊断通道</h3>
              <p className="text-[11px] text-slate-400 leading-relaxed font-light">
                全量接入 Gemini 及各类智算节点。当有代码提交事件产生，多智能体联动诊断可瞬时完成全仓库深度扫描与分析。
              </p>
            </div>
          </div>
          <span className="mt-4 w-fit px-2.5 py-1 rounded-md border border-slate-200/40 bg-slate-50 text-[9px] font-mono font-bold tracking-wider uppercase text-slate-500">
            AI_AGENT_DIAGNOSTICS
          </span>
        </div>
      </div>
    </div>
  );
}
