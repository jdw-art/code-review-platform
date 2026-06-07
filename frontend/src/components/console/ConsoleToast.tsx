import type { ReactNode } from "react";

import { ConsoleStatusPill } from "./ConsoleStatusPill";

export function ConsoleToast({
  title,
  message,
  tone = "info",
}: {
  title: string;
  message?: ReactNode;
  tone?: "danger" | "info" | "success" | "warning";
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-start gap-3">
        <ConsoleStatusPill tone={tone}>{title}</ConsoleStatusPill>
        {message ? <div className="pt-0.5 text-xs text-slate-600">{message}</div> : null}
      </div>
    </div>
  );
}
