import { useQuery } from "@tanstack/react-query";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { PageCard } from "../../components/common/PageCard";
import { StatusBadge } from "../../components/common/StatusBadge";
import { listAuditLogs } from "../../features/system/api";
import type { AuditLogResponse } from "../../lib/api/types";

const auditLogColumns: DataTableColumn<AuditLogResponse>[] = [
  {
    key: "created_at",
    title: "时间",
  },
  {
    key: "username_snapshot",
    title: "操作人",
    render: (row) => row.username_snapshot || "-",
  },
  {
    key: "action",
    title: "操作",
  },
  {
    key: "resource_type",
    title: "资源类型",
  },
  {
    key: "result",
    title: "结果",
    render: (row) => <StatusBadge value={row.result} />,
  },
];

/**
 * 系统日志页先把操作时间、执行人和结果状态这些最关键的审计摘要落出来。
 */
export function AuditLogPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", "list"],
    queryFn: () => listAuditLogs(),
  });

  return (
    <PageCard
      title="系统日志"
      description="查看后台关键操作的审计记录、执行人和结果状态。"
    >
      <DataTable
        columns={auditLogColumns}
        rows={data?.items ?? []}
        loading={isLoading}
        emptyText="暂无审计日志"
      />
    </PageCard>
  );
}
