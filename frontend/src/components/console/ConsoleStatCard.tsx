import type { ReactNode } from "react";

export function ConsoleStatCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500">{label}</p>
          <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
        </div>
        {icon ? <div className="rounded-xl bg-slate-50 p-2 text-slate-600">{icon}</div> : null}
      </div>
      {hint ? <div className="mt-3 text-xs text-slate-500">{hint}</div> : null}
    </section>
  );
}
