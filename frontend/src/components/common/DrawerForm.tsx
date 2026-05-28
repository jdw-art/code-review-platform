import type { ReactNode } from "react";

/**
 * DrawerForm 先提供最小可复用抽屉骨架，后续页面可以直接把表单内容塞进去。
 */
export function DrawerForm({
  open,
  title,
  description,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  description: string;
  onClose?: () => void;
  children: ReactNode;
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-30">
      <button
        type="button"
        aria-label="关闭抽屉"
        className="absolute inset-0 bg-slate-950/20"
        onClick={onClose}
      />
      <aside className="absolute inset-y-0 right-0 z-10 w-full max-w-xl border-l border-slate-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
          </div>
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
            >
              关闭
            </button>
          ) : null}
        </div>
        <div className="h-full overflow-y-auto p-6 pb-24">{children}</div>
      </aside>
    </div>
  );
}
