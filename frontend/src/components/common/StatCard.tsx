/**
 * StatCard 用于仪表盘概览统计，统一数字卡片的标题、数值和补充说明样式。
 */
export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <article className="overflow-hidden rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="mt-4 text-3xl font-semibold text-slate-950">{value}</p>
      {hint ? (
        <p className="mt-2 text-sm leading-6 text-slate-600">{hint}</p>
      ) : null}
    </article>
  );
}
