import type { ReactNode } from "react";

export type SidebarItem = {
  id: string;
  label: string;
  icon: ReactNode;
  shortcut?: string;
  disabled?: boolean;
};

type SidebarRailProps = {
  items: SidebarItem[];
  activeItemId: string | null;
  onSelect: (id: string) => void;
};

export function SidebarRail({ items, activeItemId, onSelect }: SidebarRailProps) {
  return (
    <div className="pointer-events-auto absolute left-4 top-6 z-40 flex w-16 flex-col items-center gap-2 overflow-visible rounded-2xl border border-slate-700/70 bg-slate-950/85 py-3 shadow-xl shadow-black/40 backdrop-blur">
      {items.map((item) => {
        const active = item.id === activeItemId;
        return (
          <button
            key={item.id}
            type="button"
            disabled={item.disabled}
            onClick={() => onSelect(item.id)}
            title={item.shortcut ? `${item.label} (${item.shortcut})` : item.label}
            className={`group relative flex h-11 w-11 items-center justify-center rounded-xl border transition ${
              active
                ? "border-cyan-400/70 bg-cyan-500/20 text-cyan-100"
                : "border-slate-700/80 bg-slate-900/70 text-slate-300 hover:border-slate-500/70 hover:text-slate-100"
            } ${item.disabled ? "cursor-not-allowed opacity-50" : ""}`}
          >
            {item.icon}
            <span className="pointer-events-none absolute left-full z-[70] ml-2 hidden whitespace-nowrap rounded border border-slate-700/70 bg-slate-950/95 px-2 py-1 text-[11px] text-slate-100 shadow-lg shadow-black/40 group-hover:block">
              {item.label}
              {item.shortcut ? ` (${item.shortcut})` : ""}
            </span>
          </button>
        );
      })}
    </div>
  );
}
