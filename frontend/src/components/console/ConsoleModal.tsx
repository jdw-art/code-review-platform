import { useEffect, useId, type ReactNode } from "react";

export function ConsoleModal({
  open,
  title,
  description,
  children,
  footer,
  onClose,
}: {
  open: boolean;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  onClose?: () => void;
}) {
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open || onClose === undefined) {
      return;
    }

    const handleClose = onClose;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        handleClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, open]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-xl"
      >
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 id={titleId} className="text-sm font-bold text-slate-900">
            {title}
          </h2>
          {description ? (
            <div id={descriptionId} className="mt-1 text-xs text-slate-500">
              {description}
            </div>
          ) : null}
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer ? <div className="border-t border-slate-200 px-5 py-4">{footer}</div> : null}
      </div>
    </div>
  );
}
