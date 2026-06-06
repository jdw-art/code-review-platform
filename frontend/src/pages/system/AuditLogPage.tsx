import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { ConsolePageHeader } from "../../components/console/ConsolePageHeader";
import { ConsoleToast } from "../../components/console/ConsoleToast";
import { StatusBadge } from "../../components/common/StatusBadge";
import { listAuditLogs, purgeAuditLogs } from "../../features/system/api";
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
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{
    title: string;
    message?: string;
    tone: "danger" | "success";
  } | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", "list"],
    queryFn: () => listAuditLogs(),
  });
  const purgeMutation = useMutation({
    mutationFn: async () => purgeAuditLogs(),
    onSuccess: async (payload) => {
      setToast({
        title: `已清理 ${payload.purged_count} 条业务审计日志。`,
        message: "系统安全日志已保留。",
        tone: "success",
      });
      await queryClient.invalidateQueries({ queryKey: ["audit-logs", "list"] });
    },
    onError: (error: Error) => {
      setToast({
        title: "清理审计日志失败。",
        message: error.message || "请稍后重试。",
        tone: "danger",
      });
    },
  });

  return (
    <div className="space-y-4 rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-violet-50/40 p-4 shadow-sm">
      {toast ? (
        <ConsoleToast title={toast.title} message={toast.message} tone={toast.tone} />
      ) : null}
      <ConsolePageHeader
        title="审计日志观测台"
        description="查看后台关键操作的执行人、资源类型与结果状态。"
        action={
          <button
            type="button"
            onClick={() => void purgeMutation.mutateAsync()}
            disabled={purgeMutation.isPending}
            className="rounded-full border border-rose-200 px-4 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {purgeMutation.isPending ? "清理中..." : "清空审计日志"}
          </button>
        }
      />
      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
        <DataTable
          columns={auditLogColumns}
          rows={data?.items ?? []}
          loading={isLoading}
          emptyText="暂无审计日志"
        />
      </section>
    </div>
  );
}
