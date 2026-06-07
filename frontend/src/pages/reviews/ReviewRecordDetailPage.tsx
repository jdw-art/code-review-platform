import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { PageCard } from "../../components/common/PageCard";
import { StatusBadge } from "../../components/common/StatusBadge";
import { getReviewRecord } from "../../features/reviews/api";

function formatEventType(value: string) {
  if (value === "merge_request") {
    return "合并请求";
  }

  if (value === "push") {
    return "Push";
  }

  return value;
}

function formatScore(value: number | null) {
  return value === null ? "-" : value.toFixed(1);
}

function formatDateTime(value: string | null) {
  if (value === null) {
    return "-";
  }

  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
  });
}

function DetailField({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <div className="mt-2 text-sm leading-6 text-slate-800">{value}</div>
    </div>
  );
}

/**
 * 审查记录详情页把标题、分支、评分和 commit 明细聚合在一起，方便管理员快速追踪一次审查。
 */
export function ReviewRecordDetailPage() {
  const params = useParams<{ reviewRecordId: string }>();
  const reviewRecordId = Number(params.reviewRecordId);
  const hasValidId = Number.isInteger(reviewRecordId) && reviewRecordId > 0;
  const { data, isLoading } = useQuery({
    queryKey: ["review-records", "detail", reviewRecordId],
    queryFn: () => getReviewRecord(reviewRecordId),
    enabled: hasValidId,
  });

  if (!hasValidId) {
    return (
      <PageCard
        title="审查记录详情"
        description="当前路由缺少合法的审查记录 ID。"
      >
        <p className="text-sm text-slate-600">请从审查记录列表重新进入详情页。</p>
      </PageCard>
    );
  }

  return (
    <section className="space-y-6">
      <PageCard
        title="审查记录详情"
        description="查看单次审查事件的基础信息、评分结果和 commit 明细。"
        actions={
          <Link
            to="/review-records"
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            返回列表
          </Link>
        }
      >
        {isLoading ? (
          <p className="text-sm text-slate-600">正在加载审查详情...</p>
        ) : data ? (
          (() => {
            const commits = data.commits ?? [];

            return (
              <div className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <DetailField label="项目名称" value={data.project_name_snapshot} />
                  <DetailField label="事件类型" value={formatEventType(data.event_type)} />
                  <DetailField label="作者" value={data.author} />
                  <DetailField label="审查状态" value={<StatusBadge value={data.review_status} />} />
                  <DetailField label="评分" value={formatScore(data.score)} />
                  <DetailField label="源分支" value={data.source_branch ?? data.branch ?? "-"} />
                  <DetailField label="目标分支" value={data.target_branch ?? "-"} />
                  <DetailField label="更新时间" value={formatDateTime(data.updated_at)} />
                </div>
                <div className="grid gap-4 xl:grid-cols-2">
                  <DetailField label="审查摘要" value={data.summary ?? data.review_result ?? "-"} />
                  <DetailField
                    label="提示词快照"
                    value={data.review_prompt_snapshot ?? "未记录提示词快照"}
                  />
                </div>
                <section className="rounded-[1.5rem] border border-slate-200">
                  <header className="border-b border-slate-200 px-5 py-4">
                    <h2 className="text-lg font-semibold text-slate-900">Commit 明细</h2>
                    <p className="mt-1 text-sm text-slate-600">
                      当前审查事件共包含 {commits.length} 条 commit 记录。
                    </p>
                  </header>
                  <div className="divide-y divide-slate-100">
                    {commits.length > 0 ? (
                      commits.map((commit) => (
                    <article key={commit.id} className="px-5 py-4">
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <p className="font-medium text-slate-900">
                          {commit.message ?? "无 commit 标题"}
                        </p>
                        <p className="text-xs text-slate-500">
                          {commit.short_commit_id ?? commit.commit_id}
                        </p>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">
                        作者：{commit.author ?? "-"} | 时间：{formatDateTime(commit.timestamp)}
                      </p>
                    </article>
                      ))
                    ) : (
                      <p className="px-5 py-6 text-sm text-slate-500">暂无 commit 明细</p>
                    )}
                  </div>
                </section>
              </div>
            );
          })()
        ) : (
          <p className="text-sm text-slate-600">未获取到审查详情。</p>
        )}
      </PageCard>
    </section>
  );
}
