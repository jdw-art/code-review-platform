import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { PageCard } from "../../components/common/PageCard";
import { StatusBadge } from "../../components/common/StatusBadge";
import { listReviewRecords } from "../../features/reviews/api";
import type { ReviewRecordListItemResponse } from "../../lib/api/types";

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

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
  });
}

const reviewRecordColumns: DataTableColumn<ReviewRecordListItemResponse>[] = [
  {
    key: "project_name_snapshot",
    title: "项目名称",
    render: (row) => (
      <div>
        <p className="font-medium text-slate-900">{row.project_name_snapshot}</p>
        <p className="text-xs text-slate-500">{row.template_name_snapshot ?? "未绑定模板"}</p>
      </div>
    ),
  },
  {
    key: "event_type",
    title: "事件类型",
    render: (row) => formatEventType(row.event_type),
  },
  {
    key: "author",
    title: "作者",
  },
  {
    key: "score",
    title: "评分",
    render: (row) => formatScore(row.score),
  },
  {
    key: "commit_messages",
    title: "提交信息",
    render: (row) => {
      const commitMessages = row.commit_messages ?? [];

      return (
        <div className="space-y-1">
          {commitMessages.length > 0 ? (
            commitMessages.slice(0, 2).map((message) => (
            <p key={message} className="max-w-xl truncate text-sm text-slate-700">
              {message}
            </p>
            ))
          ) : (
            <span className="text-slate-500">暂无提交信息</span>
          )}
        </div>
      );
    },
  },
  {
    key: "review_status",
    title: "状态",
    render: (row) => <StatusBadge value={row.review_status} />,
  },
  {
    key: "updated_at",
    title: "更新时间",
    render: (row) => formatDateTime(row.updated_at),
  },
  {
    key: "detail",
    title: "操作",
    render: (row) => (
      <Link
        to={`/review-records/${row.id}`}
        className="text-sm font-medium text-cyan-700 transition hover:text-cyan-900"
      >
        查看详情
      </Link>
    ),
  },
];

/**
 * 审查记录页先聚焦最关键的审查摘要字段，保证后台能查看项目、提交和评分结果。
 */
export function ReviewRecordListPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["review-records", "list"],
    queryFn: () => listReviewRecords({ page: 1, page_size: 20 }),
  });

  return (
    <PageCard
      title="审查记录"
      description="查看项目最近的 Push / 合并请求审查结果、评分和提交摘要。"
    >
      <DataTable
        columns={reviewRecordColumns}
        rows={data?.items ?? []}
        loading={isLoading}
        emptyText="暂无审查记录"
      />
    </PageCard>
  );
}
