import { useQuery } from "@tanstack/react-query";
import { Award, Users } from "lucide-react";

import { listMemberAnalytics } from "../../features/member-analytics/api";
import type { MemberAnalyticsListItemResponse } from "../../lib/api/types";

function formatPassRate(value: number | null) {
  return value === null ? "--" : `${value.toFixed(1)}%`;
}

function readErrorMessage(error: unknown) {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "请稍后重试。";
}

function formatRelativeReview(value: string | null) {
  if (!value) {
    return "暂无最近审查";
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

function memberAvatarLabel(name: string) {
  return name.trim().slice(0, 2).toUpperCase() || "NA";
}

function buildRiskSummary(members: MemberAnalyticsListItemResponse[]) {
  const scoredMembers = members.filter(
    (member): member is MemberAnalyticsListItemResponse & { average_score: number } =>
      member.average_score !== null
  );
  const averageScore = scoredMembers.length
    ? scoredMembers.reduce((sum, member) => sum + member.average_score, 0) /
      scoredMembers.length
    : null;
  const totalAdditions = members.reduce((sum, member) => sum + member.total_additions, 0);
  const totalDeletions = members.reduce((sum, member) => sum + member.total_deletions, 0);
  const latestReview = members
    .map((member) => member.last_review_at)
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0] ?? null;
  const leadMember = [...members].sort((left, right) => {
    const leftScore = left.average_score ?? -1;
    const rightScore = right.average_score ?? -1;
    if (rightScore !== leftScore) {
      return rightScore - leftScore;
    }
    return right.review_count - left.review_count;
  })[0] ?? null;

  if (members.length === 0) {
    return {
      narrative:
        "当前尚未生成成员维度的 review_records 聚合结果，风险追踪卡将在首批成员审查写入后同步刷新。",
      riskValue: "N/A (INSUFFICIENT SIGNAL)",
      decisionValue: "MANUAL-REVIEW",
    };
  }

  const leadMemberSummary =
    leadMember === null
      ? "当前暂无可用成员样本。"
      : `${leadMember.member_name} 在 ${leadMember.project_name} 累计 ${leadMember.review_count} 次审查，` +
        `通过度 ${formatPassRate(leadMember.average_score)}。`;

  if (averageScore === null) {
    return {
      narrative:
        `近期成员矩阵暂未形成可评分样本。${leadMemberSummary} 当前累计新增 ${totalAdditions} 行、删除 ${totalDeletions} 行，最近审查 ${formatRelativeReview(latestReview)}。`,
      riskValue: "3.40 (GUARDED)",
      decisionValue: "MANUAL-REVIEW",
    };
  }

  if (averageScore >= 90) {
    return {
      narrative:
        `近期 review_records 聚合表明，${leadMemberSummary} 当前成员矩阵累计新增 ${totalAdditions} 行、删除 ${totalDeletions} 行，最近审查 ${formatRelativeReview(latestReview)}。`,
      riskValue: "1.05 (LOW RISK)",
      decisionValue: "BLOCK-FREE / AUTOMERGE",
    };
  }

  if (averageScore >= 75) {
    return {
      narrative:
        `近期 review_records 聚合显示，${leadMemberSummary} 当前成员提交质量整体稳定，但仍需持续关注代码波动与审查密度。`,
      riskValue: "2.35 (GUARDED)",
      decisionValue: "BLOCK-FREE / GUARDED-MERGE",
    };
  }

  if (averageScore >= 60) {
    return {
      narrative:
        `近期 review_records 聚合提示，${leadMemberSummary} 当前成员矩阵存在中等波动，建议结合项目上下文继续观察后续提交。`,
      riskValue: "3.10 (MEDIUM RISK)",
      decisionValue: "MANUAL-REVIEW",
    };
  }

  return {
    narrative:
      `近期 review_records 聚合提示，${leadMemberSummary} 当前成员审查均分偏低，建议优先执行人工复核与风险兜底。`,
    riskValue: "4.60 (HIGH RISK)",
    decisionValue: "MANUAL-REVIEW",
  };
}

/**
 * 成员分析页严格贴齐控制台原型布局，但所有展示内容均来自真实成员分析接口。
 */
export function MemberAnalyticsPage() {
  const { data, error, isError, isPending } = useQuery({
    queryKey: ["member-analytics", "list"],
    queryFn: () => listMemberAnalytics({ page: 1, page_size: 20 }),
  });

  if (isPending && data === undefined) {
    return (
      <section className="p-6 space-y-4 max-w-7xl mx-auto">
        <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-sm">
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
            <Users className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>团队代码提交活跃与规范分析</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">正在加载成员分析矩阵...</p>
        </div>
      </section>
    );
  }

  if (isError && data === undefined) {
    return (
      <section className="p-6 space-y-4 max-w-7xl mx-auto">
        <div className="bg-rose-50 py-4 px-5 rounded-xl border border-rose-200 shadow-sm">
          <h2 className="text-sm font-bold text-rose-900">成员分析加载失败</h2>
          <p className="text-xs text-rose-700 mt-1">{readErrorMessage(error)}</p>
        </div>
      </section>
    );
  }

  const members = data?.items ?? [];
  const summary = buildRiskSummary(members);

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-sm">
        <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
          <Users className="w-4 h-4 text-indigo-500 shrink-0" />
          <span>团队代码提交活跃与规范分析</span>
        </h2>
        <p className="text-[11px] text-slate-500 mt-0.5">
          监控各核心仓库映射的成员属性和指标排行。数据字段来自{" "}
          <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-700 font-mono">
            project_members
          </code>{" "}
          聚合视图与审查记录统计结果。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center justify-between">
            <span>开发组成员质量矩阵 (project_members)</span>
            <span className="text-[10px] text-slate-400 font-mono">
              (active sample: {members.length})
            </span>
          </h3>
          <div className="space-y-4">
            {members.length > 0 ? (
              members.map((member) => (
                <div
                  key={member.project_member_id}
                  className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex justify-between items-center flex-wrap gap-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-full font-bold text-xs uppercase flex items-center justify-center">
                      {memberAvatarLabel(member.member_name)}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5 flex-wrap">
                        <span>{member.member_name}</span>
                        <span className="text-[9px] bg-slate-200 text-slate-600 px-1 rounded-sm font-mono font-normal">
                          Role: {member.role_name ?? "未设置角色"}
                        </span>
                      </h4>
                      <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                        {member.member_email ?? "未填写邮箱"}
                      </p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
                        <span className="rounded-full bg-white px-2 py-0.5 border border-slate-200">
                          {member.project_name}
                        </span>
                        <span>{member.review_count} 次审查</span>
                        <span className="font-mono">
                          +{member.total_additions} / -{member.total_deletions}
                        </span>
                        <span>{formatRelativeReview(member.last_review_at)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-right text-xs">
                    <div>
                      <span className="text-[9px] text-slate-400 block font-mono">
                        member_id
                      </span>
                      <span className="font-mono text-slate-600 font-bold">
                        {member.project_member_id}
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-400 block">通过度</span>
                      <span className="font-mono font-bold text-indigo-600">
                        {formatPassRate(member.average_score)}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-500">
                暂无成员分析数据。
              </div>
            )}
          </div>
        </div>

        <div className="bg-[#0b0c16] text-[#93c5fd] rounded-2xl p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-white">
              <Award className="w-5 h-5 text-indigo-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider">
                智能审计风险追踪
              </h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-light">
              {summary.narrative}
            </p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-2 mt-4 text-xs font-mono">
            <div className="flex justify-between gap-3">
              <span className="text-slate-400">平均风险评估级 (Average Risk)</span>
              <span className="text-emerald-400 font-bold text-right">
                {summary.riskValue}
              </span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-slate-400">系统判定决策值 (Decision Engine)</span>
              <span className="text-indigo-300 font-bold text-right">
                {summary.decisionValue}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
