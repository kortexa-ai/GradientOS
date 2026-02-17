import type { ReactNode } from "react";
import { X } from "lucide-react";

type SidebarDrawerProps = {
  children: ReactNode;
  onClose: () => void;
  headerContent?: ReactNode;
  widthClassName?: string;
  heightMode?: "content" | "full";
};

export function SidebarDrawer({
  children,
  onClose,
  headerContent,
  widthClassName = "w-[20rem] max-w-[calc(100vw-7rem)]",
  heightMode = "content",
}: SidebarDrawerProps) {
  return (
    <div
      className={`pointer-events-none absolute bottom-6 left-24 top-6 z-30 min-h-0 ${widthClassName}`}
    >
      <div
        className={`pointer-events-auto flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-700/60 bg-slate-900/85 shadow-lg shadow-slate-900/50 backdrop-blur-lg ${
          heightMode === "full" ? "h-full" : "max-h-full"
        }`}
      >
        <div className="flex items-start justify-between gap-2 border-b border-slate-700/50 px-3 py-2.5">
          <div className="min-w-0 flex flex-1 flex-wrap items-center gap-2">
            {headerContent ?? (
              <span className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-300/90">
                Panel
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg border border-slate-700/70 bg-slate-900/70 p-1 text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
            aria-label="Close drawer"
          >
            <X size={14} />
          </button>
        </div>
        <div className="gradient-scrollbar min-h-0 flex-1 overflow-x-hidden overflow-y-auto p-2.5 pr-1.5">
          {children}
        </div>
      </div>
    </div>
  );
}
