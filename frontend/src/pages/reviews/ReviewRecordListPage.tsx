import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  GitPullRequest,
  Sparkles,
} from "lucide-react";

import { listReviewRecords } from "../../features/reviews/api";
import type { ReviewRecordListItemResponse } from "../../lib/api/types";

function resolveScoreStatus(score: number | null) {
  if (score === null) {
    return "pending";
  }
  if (score >= 90) {
    return "excellent";
  }
  if (score >= 70) {
    return "pass";
  }
  if (score >= 60) {
    return "warning";
  }
  return "fail";
}

function renderScoreText(score: number | null) {
  if (score === null) {
    return "--";
  }
  return `${Math.round(score)}分`;
}

export function ReviewRecordListPage() {
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [expandedReviewIds, setExpandedReviewIds] = useState<Record<number, boolean>>(
    {}
  );

  const { data, isLoading } = useQuery({
    queryKey: ["review-records", "list", currentPage, pageSize],
    queryFn: () => listReviewRecords({ page: currentPage, page_size: pageSize }),
    placeholderData: keepPreviousData,
  });

  const filteredRecords = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    const records = data?.items ?? [];

    if (keyword === "") {
      return records;
    }

    return records.filter((record) => {
      const projectName = record.project_name_snapshot.toLowerCase();
      const title = (record.title ?? "").toLowerCase();
      const author = record.author.toLowerCase();

      return (
        projectName.includes(keyword) ||
        title.includes(keyword) ||
        author.includes(keyword)
      );
    });
  }, [data?.items, search]);

  const hasSearch = search.trim() !== "";
  const totalItems = hasSearch ? filteredRecords.length : (data?.total ?? 0);
  const totalPages = hasSearch ? 1 : Math.max(data?.total_pages ?? 0, 1);
  const currentRecords = filteredRecords;
  const indexOfFirstItem = totalItems === 0 ? 0 : hasSearch ? 0 : (currentPage - 1) * pageSize;
  const indexOfLastItem = totalItems === 0 ? 0 : indexOfFirstItem + currentRecords.length;

  useEffect(() => {
    setCurrentPage(1);
  }, [search, pageSize]);

  useEffect(() => {
    if (data !== undefined && currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, data, totalPages]);

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-6">
      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-5 py-3.5 shadow-3xs">
        <div>
          <h2 className="flex items-center gap-1.5 text-sm font-bold text-slate-800">
            <GitPullRequest className="h-4 w-4 shrink-0 text-indigo-500" />
            <span>智能审查记录控制中心</span>
          </h2>
          <p className="mt-0.5 text-[11px] text-slate-500">
            双向溯源全部 PR 审查评分及 diff 修改记录。数据完全对齐{" "}
            <code className="rounded bg-slate-100 px-1 text-[10px] font-mono text-indigo-650">
              review_records
            </code>{" "}
            数据表。
          </p>
        </div>
      </div>

      <div className="relative w-full max-w-md">
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="按照项目名称、提交标题、作者进行全局过滤..."
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs text-slate-800 focus:outline-hidden"
        />
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="divide-y divide-slate-100">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-slate-400">
              正在加载审查记录数据...
            </div>
          ) : currentRecords.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-400">
              暂无匹配的审查记录数据
            </div>
          ) : (
            currentRecords.map((record) => {
              const scoreStatus = resolveScoreStatus(record.score);
              const isExpanded = expandedReviewIds[record.id] ?? false;
              const summaryContent =
                record.summary ?? record.review_result ?? "暂无审查摘要。";

              return (
                <div
                  key={record.id}
                  className="flex flex-col justify-between gap-5 px-6 py-[18px] transition-colors hover:bg-slate-50/20 md:flex-row md:items-center"
                >
                  <div className="min-w-0 grow max-w-4xl space-y-2.5">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                        <span className="font-sans font-bold text-slate-800">
                          {record.project_name_snapshot}
                        </span>
                        <span className="text-slate-300">/</span>
                        <span className="rounded-xs border border-indigo-100 bg-indigo-50/50 px-1.5 py-0.2 text-indigo-600">
                          {record.branch ?? "unknown"} @{" "}
                          {record.last_commit_id?.slice(0, 10) ?? "no-commit"}
                        </span>
                        <span className="text-slate-300">|</span>
                        <span className="rounded-xs bg-slate-100 px-1.5 text-slate-500">
                          事件类型: {record.event_type}
                        </span>
                        <span className="text-slate-300">|</span>
                        <span className="text-slate-500">
                          核心托管: {record.template_name_snapshot ?? "未绑定模板"}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-900">
                        {record.title ?? "未命名审查记录"}
                      </h3>
                    </div>

                    <div className="rounded-xl border border-slate-150 bg-slate-50/50 px-3.5 py-2 text-xs font-light leading-relaxed text-slate-600">
                      <div className="mb-1 flex items-center justify-between font-bold text-slate-800">
                        <button
                          type="button"
                          aria-expanded={isExpanded}
                          aria-controls={`review-result-${record.id}`}
                          onClick={() =>
                            setExpandedReviewIds((current) => ({
                              ...current,
                              [record.id]: !isExpanded,
                            }))
                          }
                          className="flex cursor-pointer items-center gap-1.5 text-left"
                        >
                          <Sparkles className="h-3.5 w-3.5 animate-pulse text-amber-500" />
                          <span>AI 报告诊断意见 (review_result):</span>
                        </button>
                        <div className="flex gap-2 font-mono text-[9px] text-slate-400">
                          <span className="text-emerald-500">
                            +{record.additions} insertions
                          </span>
                          <span className="text-red-500">
                            -{record.deletions} deletions
                          </span>
                        </div>
                      </div>
                      <p
                        id={`review-result-${record.id}`}
                        className={`whitespace-pre-wrap break-words ${
                          isExpanded ? "" : "line-clamp-1"
                        }`}
                      >
                        {summaryContent}
                      </p>
                    </div>

                    <div className="flex items-center gap-4 font-mono text-[11px] font-light text-slate-450">
                      <span className="flex items-center gap-1 font-medium text-slate-500">
                        <span>提交开发者:</span>
                        <span className="font-bold text-slate-700">
                          {record.author}
                        </span>
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-slate-400" />
                        <span>发生于: {record.created_at}</span>
                      </span>
                      <span>•</span>
                      <span>
                        通知下发 (delivery_status):
                        <span
                          className={`ml-1 font-bold ${
                            record.review_status === "completed"
                              ? "text-emerald-600"
                              : "text-amber-600"
                          }`}
                        >
                          {record.review_status.toUpperCase()}
                        </span>
                      </span>
                    </div>
                  </div>

                  <div className="shrink-0 flex flex-col items-end gap-2 text-[9px] font-bold uppercase tracking-widest">
                    <div className="text-right">
                      <span className="mb-0.5 block text-slate-400">SCORE评分</span>
                      <span
                        className={`block rounded-xl border px-3.5 py-1.5 font-mono text-2xl ${
                          scoreStatus === "excellent"
                            ? "border-emerald-200 bg-emerald-50 font-bold text-emerald-700"
                            : scoreStatus === "pass"
                              ? "border-indigo-200 bg-indigo-50 font-bold text-indigo-700"
                              : scoreStatus === "warning"
                                ? "border-amber-200 bg-amber-50 font-bold text-amber-700"
                                : scoreStatus === "pending"
                                  ? "border-slate-200 bg-slate-50 font-bold text-slate-500"
                                  : "border-red-200 bg-red-50 font-bold text-red-700"
                        }`}
                      >
                        {renderScoreText(record.score)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {totalItems > 0 ? (
          <div className="flex flex-col items-center justify-between gap-4 border-t border-slate-100 bg-white px-6 py-4 text-xs select-none shadow-3xs sm:flex-row">
            <div className="flex flex-col items-center gap-3 font-sans text-slate-500 sm:flex-row">
              <div>
                显示{" "}
                <span className="font-semibold text-slate-800">
                  {indexOfFirstItem + 1}
                </span>{" "}
                至{" "}
                <span className="font-semibold text-slate-800">
                  {indexOfLastItem}
                </span>{" "}
                条，共{" "}
                <span className="font-semibold text-slate-800">{totalItems}</span>{" "}
                条审查记录
              </div>
              <div className="ml-0 flex items-center gap-1.5 sm:ml-4">
                <span>每页显示:</span>
                <select
                  value={pageSize}
                  onChange={(event) => {
                    setPageSize(Number(event.target.value));
                    setCurrentPage(1);
                  }}
                  className="cursor-pointer rounded-md border border-slate-205 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-850 focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                >
                  <option value={5}>5 条</option>
                  <option value={10}>10 条</option>
                  <option value={20}>20 条</option>
                  <option value={50}>50 条</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="flex cursor-pointer items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-bold text-slate-650 transition active:scale-[0.98] hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                <span>上一页</span>
              </button>

              <div className="flex items-center gap-1 px-3 font-mono text-slate-600">
                <span className="font-bold text-indigo-600">{currentPage}</span>
                <span className="text-slate-300">/</span>
                <span>{totalPages}</span>
              </div>

              <button
                type="button"
                onClick={() =>
                  setCurrentPage((prev) => Math.min(prev + 1, totalPages))
                }
                disabled={currentPage === totalPages}
                className="flex cursor-pointer items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-bold text-slate-650 transition active:scale-[0.98] hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span>下一页</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
