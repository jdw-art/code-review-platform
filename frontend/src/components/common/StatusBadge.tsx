function resolveStyles(value: string | boolean) {
  if (value === true || value === "success" || value === "启用") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }

  if (value === false || value === "failed" || value === "failure" || value === "停用") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }

  return "border-slate-200 bg-slate-100 text-slate-700";
}

function resolveText(value: string | boolean) {
  if (value === true) {
    return "启用";
  }

  if (value === false) {
    return "停用";
  }

  return String(value || "-");
}

/**
 * StatusBadge 统一处理启停状态、连通性结果等轻量状态展示。
 */
export function StatusBadge({ value }: { value: string | boolean | null }) {
  if (value === null) {
    return (
      <span className="inline-flex rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs text-slate-600">
        未知
      </span>
    );
  }

  return (
    <span
      className={[
        "inline-flex rounded-full border px-3 py-1 text-xs font-medium",
        resolveStyles(value),
      ].join(" ")}
    >
      {resolveText(value)}
    </span>
  );
}
