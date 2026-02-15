import { ChevronDown, ChevronRight } from "lucide-react";
import type { ProgramNode } from "../previewUtils";

type ProgramFeatureTreeProps = {
  root: ProgramNode | null;
  expandedNodeIds: string[];
  selectedNodeId: string | null;
  onToggleExpand: (id: string) => void;
  onSelectNode: (id: string) => void;
};

function NodeRow({
  node,
  depth,
  expanded,
  selectedNodeId,
  onToggleExpand,
  onSelectNode,
}: {
  node: ProgramNode;
  depth: number;
  expanded: Set<string>;
  selectedNodeId: string | null;
  onToggleExpand: (id: string) => void;
  onSelectNode: (id: string) => void;
}) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expanded.has(node.id);
  const isSelected = selectedNodeId === node.id;
  return (
    <>
      <div
        className={`flex items-center gap-1 rounded px-1 py-1 text-[11px] ${
          isSelected
            ? "bg-cyan-500/20 text-cyan-100"
            : "text-slate-200/90 hover:bg-slate-800/70"
        }`}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        <button
          type="button"
          onClick={() => (hasChildren ? onToggleExpand(node.id) : onSelectNode(node.id))}
          className="flex h-4 w-4 items-center justify-center text-slate-400 hover:text-slate-100"
          aria-label={hasChildren ? "Toggle node" : "Select node"}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown size={12} />
            ) : (
              <ChevronRight size={12} />
            )
          ) : (
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500/70" />
          )}
        </button>
        <button
          type="button"
          onClick={() => onSelectNode(node.id)}
          className="flex min-w-0 flex-1 items-center justify-between gap-2 text-left"
          title={node.subtitle ?? node.label}
        >
          <span className="truncate">{node.label}</span>
          {node.badge ? (
            <span className="rounded border border-slate-700/80 bg-slate-900/80 px-1.5 py-0.5 text-[10px] text-slate-300">
              {node.badge}
            </span>
          ) : null}
        </button>
      </div>
      {node.subtitle ? (
        <div
          className="truncate px-1 pb-1 text-[10px] text-slate-500"
          style={{ paddingLeft: `${depth * 12 + 24}px` }}
        >
          {node.subtitle}
        </div>
      ) : null}
      {hasChildren && isExpanded
        ? node.children.map((child) => (
            <NodeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              selectedNodeId={selectedNodeId}
              onToggleExpand={onToggleExpand}
              onSelectNode={onSelectNode}
            />
          ))
        : null}
    </>
  );
}

export function ProgramFeatureTree({
  root,
  expandedNodeIds,
  selectedNodeId,
  onToggleExpand,
  onSelectNode,
}: ProgramFeatureTreeProps) {
  const expanded = new Set(expandedNodeIds);
  return (
    <div className="pointer-events-auto absolute right-6 top-6 z-30 w-[340px] max-w-[calc(100vw-2rem)] rounded-2xl border border-slate-700/70 bg-slate-950/82 p-3 shadow-2xl shadow-black/40 backdrop-blur">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-200/80">
          Program Tree
        </span>
        <span className="text-[10px] text-slate-400">
          {root ? root.label : "No program loaded"}
        </span>
      </div>
      <div className="max-h-[52vh] overflow-y-auto rounded-lg border border-slate-800/80 bg-slate-900/35 p-1">
        {root ? (
          <NodeRow
            node={root}
            depth={0}
            expanded={expanded}
            selectedNodeId={selectedNodeId}
            onToggleExpand={onToggleExpand}
            onSelectNode={onSelectNode}
          />
        ) : (
          <div className="px-2 py-2 text-xs text-slate-500">
            Plan a trajectory or weld to populate the tree.
          </div>
        )}
      </div>
    </div>
  );
}
