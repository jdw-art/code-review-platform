export function ConsolePagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  const previousDisabled = page <= 1;
  const nextDisabled = page >= totalPages;

  return (
    <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 shadow-sm">
      <span>
        第 {page} / {Math.max(totalPages, 1)} 页
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={previousDisabled}
          onClick={() => onPageChange(page - 1)}
          className="rounded-lg border border-slate-200 px-3 py-1.5 font-semibold transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          上一页
        </button>
        <button
          type="button"
          disabled={nextDisabled}
          onClick={() => onPageChange(page + 1)}
          className="rounded-lg border border-slate-200 px-3 py-1.5 font-semibold transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          下一页
        </button>
      </div>
    </div>
  );
}
