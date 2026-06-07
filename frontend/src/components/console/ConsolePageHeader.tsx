import type { ReactNode } from "react";

export function ConsolePageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-slate-200/80 bg-white px-5 py-3.5 shadow-sm sm:flex-row sm:items-center">
      <div>
        <h2 className="text-sm font-bold text-slate-800">{title}</h2>
        <p className="mt-0.5 text-[11px] text-slate-500">{description}</p>
      </div>
      {action}
    </div>
  );
}
