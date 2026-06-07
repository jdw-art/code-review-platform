import type { ReactNode } from "react";

const statusClassMap = {
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  neutral: "border-slate-200 bg-slate-100 text-slate-600",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
} as const;

export function ConsoleStatusPill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: keyof typeof statusClassMap;
}) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold",
        statusClassMap[tone],
      ].join(" ")}
    >
      {children}
    </span>
  );
}
