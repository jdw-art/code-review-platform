import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Globe,
  ScrollText,
  Search,
  Trash2,
  User,
} from "lucide-react";

import { ConsoleToast } from "../../components/console/ConsoleToast";
import { listAuditLogs, purgeAuditLogs } from "../../features/system/api";

type ResultFilter = "all" | "success" | "failed";

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function buildLogDetails(item: {
  request_payload: Record<string, unknown>;
  error_message: string | null;
}) {
  if (item.error_message) {
    return item.error_message;
  }

  const entries = Object.entries(item.request_payload);
  if (entries.length === 0) {
    return "No additional contexts.";
  }

  return JSON.stringify(item.request_payload);
}

export function AuditLogPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [resultFilter, setResultFilter] = useState<ResultFilter>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [toast, setToast] = useState<{
    title: string;
    message?: string;
    tone: "danger" | "success";
  } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", "list", currentPage, pageSize],
    queryFn: () => listAuditLogs({ page: currentPage, page_size: pageSize }),
    placeholderData: keepPreviousData,
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

  const items = data?.items ?? [];
  const filteredLogs = useMemo(() => {
    return items.filter((item) => {
      const actionValue = item.action || "";
      const detailsValue = item.error_message || buildLogDetails(item);
      const operatorValue = item.username_snapshot || "";
      const pathValue = item.request_path || "";
      const resourceValue = item.resource_type || "";
      const searchValue = search.toLowerCase();

      const matchesSearch =
        actionValue.toLowerCase().includes(searchValue) ||
        detailsValue.toLowerCase().includes(searchValue) ||
        operatorValue.toLowerCase().includes(searchValue) ||
        pathValue.toLowerCase().includes(searchValue) ||
        resourceValue.toLowerCase().includes(searchValue);

      const isSuccess = item.result === "success";
      const matchesResult =
        resultFilter === "all" ||
        (resultFilter === "success" && isSuccess) ||
        (resultFilter === "failed" && !isSuccess);

      return matchesSearch && matchesResult;
    });
  }, [items, resultFilter, search]);

  useEffect(() => {
    setCurrentPage(1);
  }, [pageSize, resultFilter, search]);

  const hasLocalFilter = search.trim() !== "" || resultFilter !== "all";
  const totalItems = hasLocalFilter ? filteredLogs.length : (data?.total ?? 0);
  const totalPages = hasLocalFilter ? 1 : Math.max(data?.total_pages ?? 0, 1);
  const currentLogs = filteredLogs;
  const indexOfFirstItem = totalItems === 0 ? 0 : hasLocalFilter ? 0 : (currentPage - 1) * pageSize;
  const indexOfLastItem = totalItems === 0 ? 0 : indexOfFirstItem + currentLogs.length;

  useEffect(() => {
    if (data !== undefined && currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, data, totalPages]);

  function handlePurge() {
    const confirmed = window.confirm("确认清理业务审计日志吗？系统安全日志会保留。");
    if (!confirmed) {
      return;
    }

    void purgeMutation.mutateAsync();
  }

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      <h2 className="sr-only">审计日志观测台</h2>

      {toast ? (
        <ConsoleToast title={toast.title} message={toast.message} tone={toast.tone} />
      ) : null}

      <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs flex justify-between items-center flex-wrap gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
            <ScrollText className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>系统安全审计中心 (audit_logs)</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            全量监控系统底层 DDL 变更、JWT 校验与 RBAC 更新。参数字段对应 PostgreSQL{" "}
            <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-700 font-mono">
              audit_logs
            </code>{" "}
            数据表。
          </p>
        </div>

        <button
          type="button"
          onClick={handlePurge}
          disabled={purgeMutation.isPending}
          className="px-3 py-1.2 border border-red-200 hover:bg-red-50 text-red-700 text-[11px] font-bold rounded-lg flex items-center gap-1.5 cursor-pointer hover:text-red-700 transition disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>{purgeMutation.isPending ? "清理中..." : "清空审计日志"}</span>
        </button>
      </div>

      <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white px-6 py-4 rounded-xl border border-slate-200/80">
        <div className="relative w-full md:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜操作行为 action、资源、API 路径、操作人..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 text-slate-800 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 text-xs"
          />
        </div>

        <div className="flex gap-2.5">
          {(["all", "success", "failed"] as const).map((result) => (
            <button
              key={result}
              type="button"
              onClick={() => setResultFilter(result)}
              className={`px-3.5 py-1.5 text-xs font-medium rounded-xl cursor-pointer transition-all ${
                resultFilter === result
                  ? "bg-[#0b0c16] text-[#93c5fd] font-bold border border-[#2b3558]"
                  : "bg-slate-50 text-slate-500 border border-slate-200/50 hover:bg-slate-100"
              }`}
            >
              {result === "all"
                ? "全部状态"
                : result === "success"
                  ? "成功 (SUCCESS)"
                  : "拦截/失败 (FAILED)"}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto scrollbar-none">
          <table className="w-full text-left border-collapse select-none whitespace-nowrap">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs font-semibold">
                <th className="py-3 px-6 w-38">创建时间 (created_at)</th>
                <th className="py-3 px-6 w-24">执功结果</th>
                <th className="py-3 px-6 w-32">快照用户 (username)</th>
                <th className="py-3 px-6 w-44">操作类型 (action)</th>
                <th className="py-3 px-6 w-32">客端 IP (ip_address)</th>
                <th className="py-3 px-6 w-52">网络端点 (path & method)</th>
                <th className="py-3 px-6">审计说明</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 text-xs">
                    正在加载审计日志...
                  </td>
                </tr>
              ) : currentLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500 text-xs">
                    暂未匹配到对应的 audtil_logs 日志条目。
                  </td>
                </tr>
              ) : (
                currentLogs.map((item) => {
                  const logUser = item.username_snapshot || "system";
                  const isSuccess = item.result === "success";

                  return (
                    <tr key={item.id} className="hover:bg-slate-50/40 text-xs">
                      <td className="py-3.5 px-6 font-mono text-slate-500 text-[11px]">
                        {formatDateTime(item.created_at)}
                      </td>
                      <td className="py-3.5 px-6">
                        <span
                          className={`inline-flex items-center gap-1 font-mono font-bold border rounded-full px-2.5 py-0.5 text-[10px] ${
                            isSuccess
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-red-50 text-red-700 border-red-200 font-semibold"
                          }`}
                        >
                          {isSuccess ? "SUCCESS" : "FAILED"}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 font-bold text-slate-700">
                        <span className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-slate-400" />
                          <span>{logUser}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-6 font-mono text-slate-800 font-bold text-[11px]">
                        {item.action}
                      </td>
                      <td className="py-3.5 px-6 text-slate-500 font-mono text-[10px]">
                        <span className="flex items-center gap-1">
                          <Globe className="w-3.5 h-3.5 text-slate-400" />
                          <span>{item.ip_address || "127.0.0.1"}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-6 font-mono text-slate-600 text-[10px]">
                        {item.request_method ? (
                          <span className="px-1 py-0.2 bg-slate-100 rounded text-slate-700 mr-1.5 font-bold">
                            {item.request_method}
                          </span>
                        ) : null}
                        <span>{item.request_path || "/api/internal/rpc"}</span>
                      </td>
                      <td className="py-3.5 px-6 text-slate-600 max-w-xs truncate font-light text-[11px]">
                        {buildLogDetails(item)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {totalItems > 0 ? (
          <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-100 bg-white px-6 py-4 text-xs gap-4 select-none">
            <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
              <div>
                显示 <span className="font-semibold text-slate-800">{indexOfFirstItem + 1}</span> 至{" "}
                <span className="font-semibold text-slate-800">
                  {indexOfLastItem}
                </span>{" "}
                条，共 <span className="font-semibold text-slate-800">{totalItems}</span> 条记录
              </div>

              <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                <span>每页显示:</span>
                <select
                  value={pageSize}
                  onChange={(event) => {
                    setPageSize(Number(event.target.value));
                    setCurrentPage(1);
                  }}
                  className="border border-slate-200 bg-slate-50 text-slate-800 rounded-md px-2 py-1 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                >
                  <option value={5}>5 条</option>
                  <option value={10}>10 条</option>
                  <option value={20}>20 条</option>
                  <option value={50}>50 条</option>
                  <option value={100}>100 条</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.max(page - 1, 1))}
                disabled={currentPage === 1}
                className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>上一页</span>
              </button>

              <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                <span className="font-bold text-indigo-600">{currentPage}</span>
                <span className="text-slate-300">/</span>
                <span>{totalPages}</span>
              </div>

              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.min(page + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
              >
                <span>下一页</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
