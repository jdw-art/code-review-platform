import type { ReactNode } from "react";

export interface DataTableColumn<RowT> {
  key: string;
  title: string;
  render?: (row: RowT) => ReactNode;
  className?: string;
}

/**
 * DataTable 先聚焦后台列表页最常用的表格骨架，避免每个页面重复写表头和空态。
 */
export function DataTable<RowT extends { id?: number | string }>({
  columns,
  rows,
  loading = false,
  emptyText = "暂无数据",
}: {
  columns: DataTableColumn<RowT>[];
  rows: RowT[];
  loading?: boolean;
  emptyText?: string;
}) {
  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-slate-200">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={[
                    "px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-slate-500",
                    column.className ?? "",
                  ].join(" ")}
                >
                  {column.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-10 text-center text-sm text-slate-500"
                >
                  正在加载数据...
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-10 text-center text-sm text-slate-500"
                >
                  {emptyText}
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={String(row.id ?? rowIndex)} className="align-top">
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={[
                        "px-4 py-4 text-sm leading-6 text-slate-700",
                        column.className ?? "",
                      ].join(" ")}
                    >
                      {column.render
                        ? column.render(row)
                        : String(
                            (row as Record<string, unknown>)[column.key] ?? "-"
                          )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
