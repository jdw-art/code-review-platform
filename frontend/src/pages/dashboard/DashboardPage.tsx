import { useQuery } from "@tanstack/react-query";
import { Compass, ShieldCheck, SquareDashedKanban } from "lucide-react";

import { StatCard } from "../../components/common/StatCard";
import { getDashboardOverview } from "../../features/dashboard/api";
import { useAuth } from "../../lib/auth/auth-context";

const highlights = [
  {
    title: "认证上下文",
    description: "登录后自动恢复用户、角色、权限与菜单树。",
    icon: ShieldCheck,
  },
  {
    title: "后台导航",
    description: "侧边栏菜单来自后端 access-context，先保证权限入口正确。",
    icon: Compass,
  },
  {
    title: "页面接力",
    description: "项目、模板、模型、日志等页面将在后续任务陆续接入。",
    icon: SquareDashedKanban,
  },
];

/**
 * 仪表盘接入真实概览统计后，继续保留阶段性说明，帮助团队确认后台能力已接通到哪一层。
 */
export function DashboardPage() {
  const { user } = useAuth();
  const displayName = user?.nickname?.trim() || user?.username || "管理员";
  const { data } = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => getDashboardOverview(),
  });

  return (
    <section className="space-y-6">
      <div className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
        <div className="bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.14),_transparent_35%),linear-gradient(135deg,_#0f172a,_#1e293b)] px-8 py-8 text-white">
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">
            Dashboard
          </p>
          <h1 className="mt-3 text-3xl font-semibold">{displayName}，欢迎进入管理后台</h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-200">
            当前阶段已经把登录、菜单初始化和后台统一布局接上，核心统计、列表页与系统管理入口也在持续补齐。
          </p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="项目总数"
          value={data?.total_projects ?? 0}
          hint="纳入后台管理的项目数量。"
        />
        <StatCard
          label="启用项目"
          value={data?.active_projects ?? 0}
          hint="当前处于启用状态的项目。"
        />
        <StatCard
          label="审查记录"
          value={data?.total_review_records ?? 0}
          hint="累计写入的审查事件数量。"
        />
        <StatCard
          label="平均评分"
          value={data?.average_score?.toFixed(1) ?? "-"}
          hint="已评分审查记录的平均分。"
        />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {highlights.map((item) => {
          const Icon = item.icon;
          return (
            <article
              key={item.title}
              className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="inline-flex rounded-2xl bg-cyan-50 p-3 text-cyan-700">
                <Icon className="h-5 w-5" />
              </div>
              <h2 className="mt-5 text-lg font-semibold text-slate-900">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
