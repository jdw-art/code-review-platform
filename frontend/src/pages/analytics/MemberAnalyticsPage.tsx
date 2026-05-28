import { useQuery } from "@tanstack/react-query";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { PageCard } from "../../components/common/PageCard";
import { listMemberAnalytics } from "../../features/member-analytics/api";
import type { MemberAnalyticsListItemResponse } from "../../lib/api/types";

type MemberAnalyticsTableRow = MemberAnalyticsListItemResponse & {
  id: number;
};

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

const memberAnalyticsColumns: DataTableColumn<MemberAnalyticsTableRow>[] = [
  {
    key: "project_name",
    title: "项目名称",
  },
  {
    key: "member_name",
    title: "成员",
    render: (row) => (
      <div>
        <p className="font-medium text-slate-900">{row.member_name}</p>
        <p className="text-xs text-slate-500">{row.member_email ?? "未填写邮箱"}</p>
      </div>
    ),
  },
  {
    key: "role_name",
    title: "角色",
    render: (row) => row.role_name ?? "-",
  },
  {
    key: "review_count",
    title: "审查次数",
  },
  {
    key: "average_score",
    title: "平均评分",
    render: (row) => formatScore(row.average_score),
  },
  {
    key: "total_additions",
    title: "新增行数",
  },
  {
    key: "total_deletions",
    title: "删除行数",
  },
  {
    key: "last_review_at",
    title: "最近审查时间",
    render: (row) => formatDateTime(row.last_review_at),
  },
];

/**
 * 成员分析页展示项目成员的审查次数、平均分和代码改动聚合指标。
 */
export function MemberAnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["member-analytics", "list"],
    queryFn: () => listMemberAnalytics({ page: 1, page_size: 20 }),
  });
  const rows: MemberAnalyticsTableRow[] = (data?.items ?? []).map((item) => ({
    ...item,
    id: item.project_member_id,
  }));

  return (
    <PageCard
      title="成员分析"
      description="查看成员审查表现、平均评分与最近代码改动聚合结果。"
    >
      <DataTable
        columns={memberAnalyticsColumns}
        rows={rows}
        loading={isLoading}
        emptyText="暂无成员分析数据"
      />
    </PageCard>
  );
}
