import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BarChart3,
  Bot,
  Diff,
  FileCheck2,
  FolderOpen,
  GitCommit,
  GitPullRequest,
  Sparkles,
  TrendingUp,
  Users2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { ConsolePageHeader } from "../../components/console/ConsolePageHeader";
import { ConsoleStatCard } from "../../components/console/ConsoleStatCard";
import { ConsoleStatusPill } from "../../components/console/ConsoleStatusPill";
import { getDashboardOverview } from "../../features/dashboard/api";
import {
  toConsoleDashboardOverview,
  type ConsoleDashboardOverview,
} from "../../features/dashboard/serializers";
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

function reviewTone(status: string) {
  if (status === "reviewed") {
    return "success" as const;
  }
  if (status === "failed") {
    return "danger" as const;
  }
  if (status === "pending") {
    return "warning" as const;
  }
  return "neutral" as const;
}

function reviewLabel(status: string) {
  if (status === "reviewed") {
    return "已完成";
  }
  if (status === "failed") {
    return "失败";
  }
  if (status === "pending") {
    return "处理中";
  }
  return status;
}

function MetricListCard({
  title,
  subtitle,
  icon,
  items,
  metricLabel,
  metricValue,
  barClassName,
}: {
  title: string;
  subtitle: string;
  icon: ReactNode;
  items: ConsoleDashboardOverview["projectChart"];
  metricLabel: string;
  metricValue: (
    item: ConsoleDashboardOverview["projectChart"][number]
  ) => number | null;
  barClassName: string;
}) {
  const maxValue = Math.max(
    ...items
      .map((item) => metricValue(item))
      .filter((value): value is number => value !== null),
    1
  );

  return (
    <article className="rounded-[1.75rem] border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-2 text-slate-600">{icon}</div>
      </div>
      <div className="mt-5 space-y-3">
        {items.length > 0 ? (
          items.map((item) => {
            const value = metricValue(item);
            return (
              <div key={`${title}-${item.name}`} className="space-y-1.5">
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="truncate font-medium text-slate-700">{item.name}</span>
                  <span className="font-mono text-slate-500">
                    {metricLabel}: {value === null ? "-" : value.toFixed(1).replace(".0", "")}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className={`h-2 rounded-full ${
                      value === null ? "bg-slate-200" : barClassName
                    }`}
                    style={{
                      width:
                        value === null
                          ? "12%"
                          : `${Math.max((value / maxValue) * 100, 10)}%`,
                    }}
                  />
                </div>
              </div>
            );
          })
        ) : (
          <p className="rounded-2xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
            暂无可视化数据。
          </p>
        )}
      </div>
    </article>
  );
}

function DiffMetricCard({
  title,
  subtitle,
  icon,
  items,
}: {
  title: string;
  subtitle: string;
  icon: ReactNode;
  items: ConsoleDashboardOverview["projectChart"];
}) {
  const maxValue = Math.max(
    ...items.flatMap((item) => [item.additions, item.deletions]),
    1
  );

  return (
    <article className="rounded-[1.75rem] border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-2 text-slate-600">{icon}</div>
      </div>
      <div className="mt-5 space-y-4">
        {items.length > 0 ? (
          items.map((item) => (
            <div key={`${title}-${item.name}`} className="space-y-2">
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="truncate font-medium text-slate-700">{item.name}</span>
                <span className="font-mono text-slate-500">
                  +{item.additions} / -{item.deletions}
                </span>
              </div>
              <div className="space-y-1.5">
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-emerald-500"
                    style={{
                      width: `${Math.max((item.additions / maxValue) * 100, 8)}%`,
                    }}
                  />
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-rose-500"
                    style={{
                      width: `${Math.max((item.deletions / maxValue) * 100, 8)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          ))
        ) : (
          <p className="rounded-2xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
            暂无变更规模数据。
          </p>
        )}
      </div>
    </article>
  );
}

/**
 * 高保真仪表盘通过单个 overview 查询承接 Hero、KPI、监控流和分析区，避免页面层散落字段映射。
 */
export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const displayName = user?.nickname?.trim() || user?.username || "管理员";
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

  return (
    <section className="space-y-8">
      <div className="overflow-hidden rounded-[2rem] border border-slate-200/80 bg-white shadow-sm">
        <div className="relative overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.16),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.14),_transparent_30%),linear-gradient(135deg,_#f8fafc,_#e2e8f0)] px-8 py-8">
          <div className="absolute -right-20 top-0 h-56 w-56 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute bottom-0 left-0 h-48 w-48 rounded-full bg-emerald-500/10 blur-3xl" />
          <div className="relative space-y-5">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 font-semibold tracking-[0.24em] text-indigo-700">
                DASHBOARD
              </span>
              <span className="text-slate-500">
                活动模型: {overview.activeModelName ?? "未配置默认模型"}
              </span>
            </div>
            <div className="space-y-3">
              <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
                {displayName}，欢迎进入代码复审控制中心
              </h1>
              <p className="max-w-3xl text-sm leading-7 text-slate-600">
                智能代码审查控制台已接入真实概览数据。这里集中查看受管仓库、最近审查流水、
                当前启用模型以及项目与成员维度的质量趋势，帮助团队快速定位风险与产能变化。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => navigate("/projects")}
                className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                仓库项目配置
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => navigate("/models")}
                className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
              >
                切换审核模型
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ConsoleStatCard
          label="项目总数"
          value={overview.totalProjects}
          hint="纳入后台管理的仓库代码项目总数。"
          icon={<FolderOpen className="h-4 w-4" />}
        />
        <ConsoleStatCard
          label="启用项目"
          value={
            <div className="flex items-baseline gap-2">
              <span>{overview.activeProjects}</span>
              <span className="text-sm font-normal text-slate-500">
                / {overview.totalProjects}
              </span>
            </div>
          }
          hint="当前处于启用监控审查状态的项目。"
          icon={<FileCheck2 className="h-4 w-4" />}
        />
        <ConsoleStatCard
          label="审查记录"
          value={overview.totalReviewRecords}
          hint="系统累计写入并打分的审查事件总和。"
          icon={<GitPullRequest className="h-4 w-4" />}
        />
        <ConsoleStatCard
          label="平均评分"
          value={formatScore(overview.averageScore)}
          hint="全量项目已评分审查记录的总体均分。"
          icon={<TrendingUp className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <article className="rounded-[1.75rem] border border-slate-200/80 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">
                实时审查流水线监视器
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                最近触发的 PR、MR 与 push 审查事件，直接反映当前工作区的复审节奏。
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/review-records")}
              className="hidden rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 sm:block"
            >
              查看全部记录
            </button>
          </div>
          <div className="mt-5 space-y-3">
            {overview.recentReviews.length > 0 ? (
              overview.recentReviews.map((review) => (
                <div
                  key={review.id}
                  className="rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-slate-900">
                          {review.project_name}
                        </p>
                        <ConsoleStatusPill tone={reviewTone(review.review_status)}>
                          {reviewLabel(review.review_status)}
                        </ConsoleStatusPill>
                      </div>
                      <p className="text-sm text-slate-700">
                        {review.title ?? "未命名审查记录"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-indigo-700">
                        {formatScore(review.score)}
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatTimestamp(review.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span className="rounded-full bg-white px-2.5 py-1 font-mono">
                      {review.branch ?? "unknown"} @ {review.commit_hash ?? "no-hash"}
                    </span>
                    <span className="rounded-full bg-white px-2.5 py-1">
                      提交者: {review.committer ?? "unknown"}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    AI 审查摘要: {review.summary ?? "暂无摘要。"}
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-2xl bg-slate-50 px-4 py-6 text-sm text-slate-500">
                暂无最近审查记录。
              </p>
            )}
          </div>
        </article>

        <div className="space-y-6">
          <article className="rounded-[1.75rem] border border-slate-200/80 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-500" />
              <h2 className="text-lg font-semibold text-slate-950">当前智算节点</h2>
            </div>
            <div className="mt-5 space-y-3">
              {overview.models.length > 0 ? (
                overview.models.map((model) => (
                  <div
                    key={model.id}
                    className="rounded-2xl border border-slate-200/70 bg-slate-50/60 px-4 py-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          {model.name}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {model.provider} API
                          {model.temperature === null
                            ? ""
                            : ` • Temp ${model.temperature}`}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <ConsoleStatusPill
                          tone={model.is_active ? "success" : "neutral"}
                        >
                          {model.is_active ? "运行中" : "备用"}
                        </ConsoleStatusPill>
                        {model.is_default ? (
                          <span className="text-[11px] font-medium text-indigo-600">
                            默认模型
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="rounded-2xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
                  暂无模型配置。
                </p>
              )}
            </div>
          </article>

          <article className="rounded-[1.75rem] border border-slate-200/80 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <FileCheck2 className="h-4 w-4 text-indigo-600" />
              <h2 className="text-lg font-semibold text-slate-950">仓库健康审查</h2>
            </div>
            <div className="mt-5 space-y-3">
              {overview.repoHealth.length > 0 ? (
                overview.repoHealth.map((project) => (
                  <div
                    key={project.project_id}
                    className="rounded-2xl border border-slate-200/70 bg-slate-50/60 px-4 py-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          {project.name}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          最近审查 {formatTimestamp(project.last_review_at)}
                        </p>
                      </div>
                      <ConsoleStatusPill
                        tone={project.is_active ? "success" : "warning"}
                      >
                        {project.is_active ? "监控中" : "已暂停"}
                      </ConsoleStatusPill>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                      <span>均分 {formatScore(project.average_score)}</span>
                      <span>{project.review_count} 条审查</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="rounded-2xl bg-slate-50 px-4 py-5 text-sm text-slate-500">
                  暂无仓库健康数据。
                </p>
              )}
            </div>
          </article>
        </div>
      </div>

      <ConsolePageHeader
        title="研发效能可视化度量中心"
        description="基于审查日志自动聚合项目、成员的提交频次、质量得分与代码变更规模。"
        action={
          <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700">
            METRICS ACTIVE
          </div>
        }
      />

      <div className="grid gap-5 xl:grid-cols-2">
        <MetricListCard
          title="各项目代码提交频次"
          subtitle="按项目聚合最近累计审查事件。"
          icon={<GitCommit className="h-4 w-4 text-indigo-500" />}
          items={overview.projectChart}
          metricLabel="提交"
          metricValue={(item) => item.commits}
          barClassName="bg-indigo-500"
        />
        <MetricListCard
          title="团队成员提交热度"
          subtitle="帮助快速识别当前最活跃的提交者。"
          icon={<Users2 className="h-4 w-4 text-emerald-500" />}
          items={overview.memberChart}
          metricLabel="提交"
          metricValue={(item) => item.commits}
          barClassName="bg-emerald-500"
        />
        <MetricListCard
          title="各项目代码质量平均得分趋势"
          subtitle="均分越高，说明近期审查反馈越稳定。"
          icon={<BarChart3 className="h-4 w-4 text-violet-500" />}
          items={overview.projectChart}
          metricLabel="均分"
          metricValue={(item) => item.avg_score}
          barClassName="bg-violet-500"
        />
        <MetricListCard
          title="成员代码质量评分指数"
          subtitle="聚焦个人维度的得分分布。"
          icon={<Bot className="h-4 w-4 text-pink-500" />}
          items={overview.memberChart}
          metricLabel="均分"
          metricValue={(item) => item.avg_score}
          barClassName="bg-pink-500"
        />
        <DiffMetricCard
          title="项目代码变更规模控制"
          subtitle="绿色表示新增，红色表示删除。"
          icon={<Diff className="h-4 w-4 text-sky-500" />}
          items={overview.projectChart}
        />
        <DiffMetricCard
          title="成员代码变更差异度量"
          subtitle="从成员侧观察代码变更规模。"
          icon={<Diff className="h-4 w-4 text-teal-500" />}
          items={overview.memberChart}
        />
      </div>
    </section>
  );
}
