/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { ScrollText, Search, ShieldAlert, CheckCircle, Info, Trash2, Globe, Server, User, ChevronLeft, ChevronRight } from 'lucide-react';
import { SystemLogItem } from '../types';

interface SystemLogsViewProps {
  logs: SystemLogItem[];
  onClearLogs?: () => void;
  onAddCustomLog?: (action: string, details: string) => void;
}

export default function SystemLogsView({ logs, onClearLogs, onAddCustomLog }: SystemLogsViewProps) {
  const [search, setSearch] = useState('');
  const [resultFilter, setResultFilter] = useState<'all' | 'success' | 'failed'>('all');
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, resultFilter, pageSize]);

  const filteredLogs = logs.filter((log) => {
    const actionVal = log.action || '';
    const detailsVal = log.details || log.error_message || '';
    const operatorVal = log.username_snapshot || log.operator || '';
    const pathVal = log.request_path || '';

    const matchesSearch =
      actionVal.toLowerCase().includes(search.toLowerCase()) ||
      detailsVal.toLowerCase().includes(search.toLowerCase()) ||
      operatorVal.toLowerCase().includes(search.toLowerCase()) ||
      pathVal.toLowerCase().includes(search.toLowerCase());

    const isSuccess = log.result === 'success';
    const matchesResult =
      resultFilter === 'all' ||
      (resultFilter === 'success' && isSuccess) ||
      (resultFilter === 'failed' && !isSuccess);

    return matchesSearch && matchesResult;
  });

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      {/* Header Block bar */}
      <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs flex justify-between items-center flex-wrap gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
            <ScrollText className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>系统安全审计中心 (audit_logs)</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            全量监控系统底层 DDL 变更、JWT 校验与 RBAC 更新。参数字段对应 PostgreSQL <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-650 font-mono">audit_logs</code> 数据表。
          </p>
        </div>

        {onClearLogs && (
          <button
            onClick={onClearLogs}
            className="px-3 py-1.2 border border-red-200 hover:bg-red-50 text-red-650 text-[11px] font-bold rounded-lg flex items-center gap-1.2 cursor-pointer hover:text-red-700 transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>清空审计日志</span>
          </button>
        )}
      </div>

      {/* Toolbar filters box */}
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white px-6 py-4 rounded-xl border border-slate-200/80">
        {/* Search */}
        <div className="relative w-full md:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜操作行为 action、资源、API 路径、操作人..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 text-slate-800 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 text-xs"
          />
        </div>

        {/* Success/Fail Filters tabs */}
        <div className="flex gap-2.5">
          {(['all', 'success', 'failed'] as const).map((res) => (
            <button
              key={res}
              onClick={() => setResultFilter(res)}
              className={`px-3.5 py-1.5 text-xs font-medium rounded-xl cursor-pointer transition-all ${
                resultFilter === res
                  ? 'bg-[#0b0c16] text-[#93c5fd] font-bold border border-[#2b3558]'
                  : 'bg-slate-50 text-slate-500 border border-slate-200/50 hover:bg-slate-100'
              }`}
            >
              {res === 'all'
                ? '全部状态'
                : res === 'success'
                ? '成功 (SUCCESS)'
                : '拦截/失败 (FAILED)'}
            </button>
          ))}
        </div>
      </div>

      {/* Real Logs Table/List Console layout */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto scrollbar-none">
          <table className="w-full text-left border-collapse select-none whitespace-nowrap">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-450 text-xs font-semibold">
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
              {(() => {
                const totalItems = filteredLogs.length;
                const indexOfLastItem = currentPage * pageSize;
                const indexOfFirstItem = Math.max(0, indexOfLastItem - pageSize);
                const currentLogs = filteredLogs.slice(indexOfFirstItem, indexOfLastItem);

                if (currentLogs.length === 0) {
                  return (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-450 text-xs">
                        暂未匹配到对应的 audtil_logs 日志条目。
                      </td>
                    </tr>
                  );
                }

                return currentLogs.map((log) => {
                  const logDate = log.created_at || log.timestamp;
                  const logUser = log.username_snapshot || log.operator || 'system';
                  const isSuccess = log.result === 'success';

                  return (
                    <tr key={log.id} className="hover:bg-slate-50/40 text-xs">
                      {/* Timestamp */}
                      <td className="py-3.5 px-6 font-mono text-slate-500 text-[11px]">
                        {logDate}
                      </td>

                      {/* Level / Result */}
                      <td className="py-3.5 px-6">
                        <span
                          className={`inline-flex items-center gap-1 font-mono font-bold border rounded-full px-2.5 py-0.5 text-[10px] ${
                            isSuccess
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-150'
                              : 'bg-red-50 text-red-700 border-red-150 font-semibold'
                          }`}
                        >
                          {isSuccess ? 'SUCCESS' : 'FAILED'}
                        </span>
                      </td>

                      {/* Operator Username */}
                      <td className="py-3.5 px-6 font-bold text-slate-700">
                        <span className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 text-slate-400" />
                          <span>{logUser}</span>
                        </span>
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-6 font-mono text-slate-800 font-bold text-[11px]">
                        {log.action}
                      </td>

                      {/* IP Addr */}
                      <td className="py-3.5 px-6 text-slate-500 font-mono text-[10px]">
                        <span className="flex items-center gap-1">
                          <Globe className="w-3.5 h-3.5 text-slate-400" />
                          <span>{log.ip_address || '127.0.0.1'}</span>
                        </span>
                      </td>

                      {/* Path & Method */}
                      <td className="py-3.5 px-6 font-mono text-slate-600 text-[10px]">
                        {log.request_method && (
                          <span className="px-1 py-0.2 bg-slate-100 rounded text-slate-700 mr-1.5 font-bold">
                            {log.request_method}
                          </span>
                        )}
                        <span>{log.request_path || '/api/internal/rpc'}</span>
                      </td>

                      {/* Details (Description) */}
                      <td className="py-3.5 px-6 text-slate-550 max-w-xs truncate font-light text-[11px]">
                        {log.details || log.error_message || 'No additional contexts.'}
                      </td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
        {/* Pagination bar */}
        {(() => {
          const totalItems = filteredLogs.length;
          const totalPages = Math.ceil(totalItems / pageSize) || 1;
          const indexOfLastItem = currentPage * pageSize;
          const indexOfFirstItem = Math.max(0, indexOfLastItem - pageSize);

          if (totalItems === 0) return null;

          return (
            <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-100 bg-white px-6 py-4 text-xs gap-4 select-none">
              <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
                <div>
                  显示 <span className="font-semibold text-slate-800">{indexOfFirstItem + 1}</span> 至{' '}
                  <span className="font-semibold text-slate-800">{Math.min(indexOfLastItem, totalItems)}</span> 条，
                  共 <span className="font-semibold text-slate-800">{totalItems}</span> 条记录
                </div>
                <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                  <span>每页显示:</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
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
                  onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
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
                  onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                >
                  <span>下一页</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
