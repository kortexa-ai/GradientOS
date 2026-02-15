import type { ReactNode } from "react";
import { X } from "lucide-react";

type SidebarDrawerProps = {
  children: ReactNode;
  onClose: () => void;
};

export function SidebarDrawer({ children, onClose }: SidebarDrawerProps) {
  return (
    <div className="pointer-events-auto absolute left-24 top-6 z-30 w-[20rem] max-w-[calc(100vw-7rem)]">
      <button
        type="button"
        onClick={onClose}
        className="absolute right-3 top-4 z-10 rounded-lg border border-slate-700/70 bg-slate-900/70 p-1 text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
        aria-label="Close drawer"
      >
        <X size={14} />
      </button>
      <div>{children}</div>
    </div>
  );
}
