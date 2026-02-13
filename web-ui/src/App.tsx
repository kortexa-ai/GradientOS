import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Camera,
  CameraOff,
  ChevronDown,
  ChevronRight,
  Home,
  Moon,
  Octagon,
  Play,
  Plug,
  RefreshCcw,
  Route,
  Settings,
  Trash2,
  Unplug,
  Undo2,
  X,
} from "lucide-react";
import { resolveDefaultApiHost, resolveDefaultVisionHost } from "./useEndpoint";
import {
  ArmVisualizer,
  type ArmVisualizerHandle,
  type StepLoadStatus,
  type StepTransform,
} from "./ArmVisualizer";
import { TelemetryCharts } from "./TelemetryCharts";
import ControlPanel from "./ControlPanel";
import {
  encodePointsForApi,
  previewFromPlannerPayload,
  previewFromTrajectoryDetail,
  type Point3,
  type PreviewPlan,
} from "./previewUtils";

type Alert = {
  level: "error" | "warning" | "info";
  kind: string;
  message: string;
  servo_ids?: number[];
  ts?: number;
  details?: Record<string, unknown>;
};

type ServoSample = {
  voltage_v?: number;
  temp_c?: number;
  current_a?: number;
  drive_duty_per_mille?: number;
  unloading_condition?: number;
  led_alarm_condition?: number;
  unloading_bits?: string;
  led_alarm_bits?: string;
};

type TelemetryEvent = {
  timestamp: number;
  raw: string;
  joints?: number[];
  gripper?: number;
  servos?: Record<string, ServoSample>;
  alerts?: Alert[];
};

type PersistedSettings = {
  showBoundingBox: boolean;
  collapseLiveCharts: boolean;
  collapseStepImport: boolean;
  collapseTrajectory: boolean;
  collapseRobotControl: boolean;
};

const SETTINGS_STORAGE_KEY = "gradient-ui:settings";
const DEFAULT_STEP_TRANSFORM: StepTransform = {
  position: { x: 0, y: 0, z: 0 },
  rotationDeg: { x: 0, y: 0, z: 0 },
  scale: 1,
};

function loadPersistedSettings(): PersistedSettings {
  const defaults: PersistedSettings = {
    showBoundingBox: true,
    collapseLiveCharts: false,
    collapseStepImport: false,
    collapseTrajectory: false,
    collapseRobotControl: false,
  };
  if (typeof window === "undefined") {
    return defaults;
  }
  try {
    const stored = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!stored) {
      return defaults;
    }
    const parsed = JSON.parse(stored);
    if (parsed && typeof parsed === "object") {
      return {
        showBoundingBox:
          typeof parsed.showBoundingBox === "boolean"
            ? parsed.showBoundingBox
            : defaults.showBoundingBox,
        collapseLiveCharts:
          typeof parsed.collapseLiveCharts === "boolean"
            ? parsed.collapseLiveCharts
            : defaults.collapseLiveCharts,
        collapseStepImport:
          typeof parsed.collapseStepImport === "boolean"
            ? parsed.collapseStepImport
            : defaults.collapseStepImport,
        collapseTrajectory:
          typeof parsed.collapseTrajectory === "boolean"
            ? parsed.collapseTrajectory
            : defaults.collapseTrajectory,
        collapseRobotControl:
          typeof parsed.collapseRobotControl === "boolean"
            ? parsed.collapseRobotControl
            : defaults.collapseRobotControl,
      };
    }
  } catch {
    // ignore malformed storage
  }
  return defaults;
}

function persistSettings(settings: PersistedSettings) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify(settings),
    );
  } catch {
    // best-effort persistence; ignore quota errors
  }
}

function normaliseApiHost(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) {
    return resolveDefaultApiHost();
  }
  return trimmed.replace(/\/+$/, "");
}

function normaliseVisionHost(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) {
    return resolveDefaultVisionHost();
  }
  return trimmed.replace(/\/+$/, "");
}

function TelemetryPanel({ latest }: { latest: TelemetryEvent | null }) {
  return (
    <div className="pointer-events-auto w-full max-w-xs rounded-xl border border-slate-700/60 bg-slate-900/80 p-4 shadow-lg shadow-slate-900/50 backdrop-blur-lg">
      {latest ? (
        <div className="flex flex-col gap-3 text-sm">
          <div className="flex items-center justify-between text-xs text-slate-300/80">
            <span className="font-medium text-slate-100">Received</span>
            <span>{new Date(latest.timestamp).toLocaleTimeString()}</span>
          </div>
          {latest.joints && latest.joints.length > 0 && (
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300/80">
                Joints (deg)
              </span>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-slate-100/90">
                {latest.joints.map((value, index) => {
                  const degrees = value * (180 / Math.PI);
                  return (
                    <li key={index}>
                      <span className="text-slate-400">J{index + 1}:</span>{" "}
                      {degrees.toFixed(1)}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          {typeof latest.gripper === "number" && (
            <div className="text-sm text-slate-100/90">
              <span className="font-semibold text-cyan-200">Gripper</span>{" "}
              {latest.gripper.toFixed(3)}
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-300/80">
          No telemetry yet. Connect to the API and start streaming.
        </p>
      )}
    </div>
  );
}

type CollapsibleOverlayPanelProps = {
  title: string;
  collapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
  widthClassName?: string;
};

function CollapsibleOverlayPanel({
  title,
  collapsed,
  onToggle,
  children,
  widthClassName = "w-full max-w-xs",
}: CollapsibleOverlayPanelProps) {
  return (
    <div className={`pointer-events-auto ${widthClassName}`}>
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between rounded-lg border border-slate-700/60 bg-slate-900/80 px-3 py-2 text-left shadow-md shadow-slate-900/30 backdrop-blur transition hover:border-slate-500/70"
      >
        <span className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-200/80">
          {title}
        </span>
        {collapsed ? (
          <ChevronRight size={16} className="text-slate-300/80" />
        ) : (
          <ChevronDown size={16} className="text-slate-300/80" />
        )}
      </button>
      {!collapsed && <div className="mt-2">{children}</div>}
    </div>
  );
}

type StepImportPanelProps = {
  stepFileName: string | null;
  stepStatus: StepLoadStatus;
  transform: StepTransform;
  onFileChange: (file: File | null) => void;
  onTransformChange: (
    group: "position" | "rotationDeg",
    axis: "x" | "y" | "z",
    value: number,
  ) => void;
  onScaleChange: (value: number) => void;
  onResetTransform: () => void;
  onClearFile: () => void;
};

function StepImportPanel({
  stepFileName,
  stepStatus,
  transform,
  onFileChange,
  onTransformChange,
  onScaleChange,
  onResetTransform,
  onClearFile,
}: StepImportPanelProps) {
  const statusTone =
    stepStatus.state === "error"
      ? "text-rose-300"
      : stepStatus.state === "loaded"
      ? "text-emerald-300"
      : stepStatus.state === "loading"
      ? "text-amber-200"
      : "text-slate-300/80";
  const parseOrKeep = (raw: string, fallback: number) => {
    const parsed = Number.parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  return (
    <div className="pointer-events-auto w-full max-w-xs rounded-xl border border-slate-700/60 bg-slate-900/80 p-4 shadow-lg shadow-slate-900/50 backdrop-blur-lg">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-200/80">
          STEP Import
        </span>
        <button
          type="button"
          onClick={onResetTransform}
          className="rounded-lg border border-slate-600/60 bg-slate-900/60 px-2 py-1 text-xs font-semibold text-slate-100 transition hover:border-slate-400 hover:text-slate-50"
        >
          Reset Pose
        </button>
      </div>
      <div className="mb-3 flex items-center gap-2">
        <label className="flex-1 cursor-pointer rounded-lg border border-slate-600/60 bg-slate-900/60 px-3 py-2 text-center text-xs font-semibold text-slate-100 transition hover:border-slate-400 hover:text-slate-50">
          Load .step/.stp
          <input
            type="file"
            accept=".step,.stp,model/step"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              onFileChange(file);
            }}
          />
        </label>
        <button
          type="button"
          onClick={onClearFile}
          disabled={!stepFileName}
          className={`rounded-lg border border-slate-600/60 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-100 transition hover:border-slate-400 hover:text-slate-50 ${
            stepFileName ? "" : "cursor-not-allowed opacity-60"
          }`}
        >
          Clear
        </button>
      </div>
      <p className="truncate text-xs text-slate-300/80">
        File:{" "}
        <span className="font-semibold text-slate-100">
          {stepFileName ?? "None"}
        </span>
      </p>
      <p className="mt-1 text-xs text-cyan-200/80">
        Frame: world (Z-up). +X red, +Y green, +Z blue.
      </p>
      <p className={`mt-1 text-xs ${statusTone}`}>{stepStatus.message}</p>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {(["x", "y", "z"] as const).map((axis) => (
          <label
            key={`pos-${axis}`}
            className="flex flex-col gap-1 rounded-lg border border-slate-700/60 bg-slate-950/40 px-2 py-2 text-[11px] text-slate-300/90"
          >
            P{axis.toUpperCase()} (m)
            <input
              className="rounded bg-slate-900/70 px-2 py-1 text-xs text-slate-100 outline-none ring-1 ring-slate-700/70 focus:ring-cyan-500/50"
              type="number"
              step="0.01"
              value={transform.position[axis]}
              onChange={(event) =>
                onTransformChange(
                  "position",
                  axis,
                  parseOrKeep(event.target.value, transform.position[axis]),
                )
              }
            />
          </label>
        ))}
        {(["x", "y", "z"] as const).map((axis) => (
          <label
            key={`rot-${axis}`}
            className="flex flex-col gap-1 rounded-lg border border-slate-700/60 bg-slate-950/40 px-2 py-2 text-[11px] text-slate-300/90"
          >
            R{axis.toUpperCase()} (deg)
            <input
              className="rounded bg-slate-900/70 px-2 py-1 text-xs text-slate-100 outline-none ring-1 ring-slate-700/70 focus:ring-cyan-500/50"
              type="number"
              step="1"
              value={transform.rotationDeg[axis]}
              onChange={(event) =>
                onTransformChange(
                  "rotationDeg",
                  axis,
                  parseOrKeep(event.target.value, transform.rotationDeg[axis]),
                )
              }
            />
          </label>
        ))}
        <label className="col-span-3 flex items-center justify-between rounded-lg border border-slate-700/60 bg-slate-950/40 px-2 py-2 text-xs text-slate-300/90">
          <span>Scale</span>
          <input
            className="w-24 rounded bg-slate-900/70 px-2 py-1 text-right text-xs text-slate-100 outline-none ring-1 ring-slate-700/70 focus:ring-cyan-500/50"
            type="number"
            min="0.01"
            step="0.1"
            value={transform.scale}
            onChange={(event) =>
              onScaleChange(parseOrKeep(event.target.value, transform.scale))
            }
          />
        </label>
      </div>
    </div>
  );
}

type TrajectoryPanelProps = {
  isPlanning: boolean;
  isPlanLoading: boolean;
  isRunning: boolean;
  preview: PreviewPlan | null;
  plannerPoints: Point3[];
  savedTrajectories: string[];
  selectedTrajectory: string;
  isTrajectoryListLoading: boolean;
  isLoadingSavedTrajectory: boolean;
  onPlanToggle: () => void;
  onRun: () => void;
  onClear: () => void;
  onRefreshTrajectories: () => void;
  onSelectTrajectory: (value: string) => void;
  onLoadTrajectory: () => void;
  onUndoPoint: () => void;
};

function TrajectoryPanel({
  isPlanning,
  isPlanLoading,
  isRunning,
  preview,
  plannerPoints,
  savedTrajectories,
  selectedTrajectory,
  isTrajectoryListLoading,
  isLoadingSavedTrajectory,
  onPlanToggle,
  onRun,
  onClear,
  onRefreshTrajectories,
  onSelectTrajectory,
  onLoadTrajectory,
  onUndoPoint,
}: TrajectoryPanelProps) {
  const waypointList = preview?.waypoints ?? plannerPoints;
  const waypointCount = waypointList.length;
  const hasSavedTrajectories = savedTrajectories.length > 0;
  const lastPoint =
    waypointList.length > 0 ? waypointList[waypointList.length - 1] : null;

  return (
    <div className="pointer-events-auto w-full max-w-xs rounded-xl border border-slate-700/60 bg-slate-900/80 p-4 shadow-lg shadow-slate-900/50 backdrop-blur-lg">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-200/80">
          Trajectory
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onPlanToggle}
            disabled={isPlanLoading || isRunning}
            className={`rounded-full border border-slate-600/50 p-2 transition ${
              isPlanning
                ? "bg-cyan-500/80 text-slate-950 shadow-inner shadow-cyan-400/40"
                : "bg-slate-900/60 text-slate-200 hover:border-slate-400 hover:text-slate-100"
            } ${isPlanLoading || isRunning ? "opacity-60" : ""}`}
            aria-label="Select trajectory target"
          >
            <Route size={18} strokeWidth={2} />
          </button>
          <button
            type="button"
            onClick={onUndoPoint}
            disabled={plannerPoints.length === 0 || isPlanLoading || isRunning}
            className={`rounded-full border border-slate-600/50 bg-slate-900/60 p-2 text-slate-200 transition hover:border-slate-400 hover:text-slate-100 ${
              plannerPoints.length === 0 || isPlanLoading || isRunning
                ? "opacity-60"
                : ""
            }`}
            aria-label="Remove last waypoint"
          >
            <Undo2 size={18} strokeWidth={2} />
          </button>
          <button
            type="button"
            onClick={onRun}
            disabled={!preview || isPlanLoading || isRunning}
            className={`rounded-full border border-slate-600/50 bg-slate-900/60 p-2 text-slate-200 transition hover:border-slate-400 hover:text-slate-100 ${
              (!preview || isPlanLoading || isRunning) ? "opacity-60" : ""
            }`}
            aria-label="Execute planned trajectory"
          >
            <Play size={18} strokeWidth={2} />
          </button>
          <button
            type="button"
            onClick={onClear}
            disabled={(!preview && !isPlanning) || isPlanLoading}
            className={`rounded-full border border-slate-600/50 bg-slate-900/60 p-2 text-slate-200 transition hover:border-slate-400 hover:text-slate-100 ${
              ((!preview && !isPlanning) || isPlanLoading) ? "opacity-60" : ""
            }`}
            aria-label="Clear planned trajectory"
          >
            <Trash2 size={18} strokeWidth={2} />
          </button>
        </div>
      </div>
      <div className="text-sm text-slate-100/90">
        {isPlanLoading ? (
          <p>Planning preview trajectory…</p>
        ) : isRunning ? (
          <p>Executing trajectory…</p>
        ) : isPlanning ? (
          <p>
            Shift-click in the workspace to add waypoints. Use undo to remove
            the last point.
          </p>
        ) : preview ? (
          <div className="flex flex-col gap-2">
            <div className="text-xs text-slate-300/80">
              Loaded:{" "}
              <span className="font-semibold text-slate-100">{preview.name}</span>
            </div>
            <div className="text-xs text-slate-300/80">
              Waypoints:{" "}
              <span className="font-semibold text-slate-100">{waypointCount}</span>
            </div>
            {lastPoint && (
              <div className="text-xs text-slate-300/80">
                Last point (m):{" "}
                <span className="font-semibold text-slate-100">
                  {lastPoint.x.toFixed(3)}, {lastPoint.y.toFixed(3)},{" "}
                  {lastPoint.z.toFixed(3)}
                </span>
              </div>
            )}
          </div>
        ) : (
          <p>No preview loaded yet.</p>
        )}
      </div>
      <div className="mt-4 border-t border-slate-700/50 pt-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-200/80">
            Saved Trajectories
          </span>
          <button
            type="button"
            onClick={onRefreshTrajectories}
            disabled={isTrajectoryListLoading}
            className={`rounded-full border border-slate-600/50 bg-slate-900/60 p-2 text-slate-200 transition hover:border-slate-400 hover:text-slate-100 ${
              isTrajectoryListLoading ? "cursor-wait opacity-60" : ""
            }`}
            aria-label="Refresh saved trajectories"
          >
            <RefreshCcw
              size={16}
              strokeWidth={2}
              className={isTrajectoryListLoading ? "animate-spin" : ""}
            />
          </button>
        </div>
        {isTrajectoryListLoading ? (
          <p className="text-xs text-slate-300/80">Loading trajectories…</p>
        ) : hasSavedTrajectories ? (
          <div className="flex items-center gap-2">
            <select
              className="flex-1 rounded-lg border border-slate-600/70 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
              value={selectedTrajectory}
              onChange={(event) => onSelectTrajectory(event.target.value)}
            >
              {savedTrajectories.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={onLoadTrajectory}
              disabled={!selectedTrajectory || isLoadingSavedTrajectory}
              className={`rounded-lg border border-slate-600/60 bg-slate-900/60 px-3 py-2 text-sm font-semibold text-slate-100 transition hover:border-slate-400 hover:text-slate-50 ${
                (!selectedTrajectory || isLoadingSavedTrajectory)
                  ? "cursor-not-allowed opacity-60"
                  : ""
              }`}
              aria-label="Load selected trajectory"
            >
              {isLoadingSavedTrajectory ? "Loading…" : "Load"}
            </button>
          </div>
        ) : (
          <p className="text-xs text-slate-300/80">
            No saved trajectories available.
          </p>
        )}
      </div>
    </div>
  );
}

type SettingsDialogProps = {
  isOpen: boolean;
  apiHost: string;
  visionHost: string;
  showBoundingBox: boolean;
  onHostChange: (value: string) => void;
  onVisionHostChange: (value: string) => void;
  onShowBoundingBoxChange: (value: boolean) => void;
  onClose: () => void;
};

function SettingsDialog({
  isOpen,
  apiHost,
  visionHost,
  showBoundingBox,
  onHostChange,
  onVisionHostChange,
  onShowBoundingBoxChange,
  onClose,
}: SettingsDialogProps) {
  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-700/60 bg-slate-900/90 p-6 shadow-2xl shadow-slate-950/60">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-cyan-200">Settings</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-600/60 p-1 text-slate-300 transition hover:border-slate-400 hover:text-slate-100"
            aria-label="Close settings"
          >
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-slate-200/90">
            Gradient API Host
            <input
              className="mt-1 w-full rounded-lg border border-slate-600/70 bg-slate-950/60 px-4 py-2 text-base text-slate-100 placeholder:text-slate-400 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
              type="text"
              value={apiHost}
              onChange={(event) => onHostChange(event.target.value)}
              placeholder="http://localhost:4000"
              autoComplete="off"
            />
          </label>
          <p className="text-xs text-slate-400/90">
            Provide the base URL for the telemetry API. Changes apply
            immediately and persist for the next connection attempt.
          </p>
          <label className="mt-4 text-sm font-medium text-slate-200/90">
            Gradient Vision Host
            <input
              className="mt-1 w-full rounded-lg border border-slate-600/70 bg-slate-950/60 px-4 py-2 text-base text-slate-100 placeholder:text-slate-400 focus:border-cyan-400/60 focus:outline-none focus:ring-2 focus:ring-cyan-500/30"
              type="text"
              value={visionHost}
              onChange={(event) => onVisionHostChange(event.target.value)}
              placeholder="http://localhost:8080"
              autoComplete="off"
            />
          </label>
          <p className="text-xs text-slate-400/90">
            MJPEG endpoint for the camera overlay. Leave blank to default to
            the current origin on port 8080.
          </p>
          <label className="mt-4 flex items-center gap-3 text-sm font-medium text-slate-200/90">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border border-slate-600 bg-slate-900 text-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
              checked={showBoundingBox}
              onChange={(event) => onShowBoundingBoxChange(event.target.checked)}
            />
            Show arm bounding box
          </label>
        </div>
      </div>
    </div>
  );
}

function AlertsPanel({
  alerts,
  onDismiss,
}: {
  alerts: Alert[];
  onDismiss: (index: number) => void;
}) {
  if (!alerts || alerts.length === 0) {
    return null;
  }
  const colorFor = (lvl: Alert["level"]) =>
    lvl === "error"
      ? "border-rose-500/50 bg-rose-500/10 text-rose-100"
      : lvl === "warning"
      ? "border-amber-500/50 bg-amber-500/10 text-amber-100"
      : "border-cyan-500/40 bg-cyan-500/10 text-cyan-100";
  const iconFor = (lvl: Alert["level"]) =>
    lvl === "error" ? <Octagon size={16} /> : lvl === "warning" ? <Octagon size={16} /> : <Octagon size={16} />;
  return (
    <div className="pointer-events-auto flex max-w-sm flex-col gap-2">
      {alerts.slice(-4).map((a, idx) => (
        <div
          key={`${a.kind}:${a.ts ?? idx}:${idx}`}
          className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm shadow-md ${colorFor(a.level)}`}
        >
          <div className="mt-0.5 shrink-0">{iconFor(a.level)}</div>
          <div className="flex-1">
            <div className="font-medium">{a.message}</div>
            {a.servo_ids && a.servo_ids.length > 0 && (
              <div className="text-xs opacity-75">Servos: {a.servo_ids.join(", ")}</div>
            )}
          </div>
          <button
            type="button"
            className="ml-2 rounded p-1 text-current/70 hover:text-current"
            aria-label="Dismiss alert"
            onClick={() => onDismiss(idx)}
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [apiHost, setApiHost] = useState(() => resolveDefaultApiHost());
  const [visionHost, setVisionHost] = useState(() => resolveDefaultVisionHost());
  const [settings, setSettings] = useState<PersistedSettings>(() => loadPersistedSettings());
  const [isConnected, setIsConnected] = useState(false);
  const [latest, setLatest] = useState<TelemetryEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [visionError, setVisionError] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [hasAttemptedAutoConnect, setHasAttemptedAutoConnect] = useState(false);
  const [isVisionActive, setIsVisionActive] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [previewPlan, setPreviewPlan] = useState<PreviewPlan | null>(null);
  const [plannerPoints, setPlannerPoints] = useState<Point3[]>([]);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isPlanLoading, setIsPlanLoading] = useState(false);
  const [isRunningPreview, setIsRunningPreview] = useState(false);
  const [savedTrajectories, setSavedTrajectories] = useState<string[]>([]);
  const [isTrajectoryListLoading, setIsTrajectoryListLoading] = useState(false);
  const [selectedTrajectory, setSelectedTrajectory] = useState("");
  const [isLoadingSavedTrajectory, setIsLoadingSavedTrajectory] = useState(false);
  const [isHoming, setIsHoming] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isResting, setIsResting] = useState(false);
  const [stepFile, setStepFile] = useState<File | null>(null);
  const [stepTransform, setStepTransform] = useState<StepTransform>(
    DEFAULT_STEP_TRANSFORM,
  );
  const [stepLoadStatus, setStepLoadStatus] = useState<StepLoadStatus>({
    state: "idle",
    message: "No STEP model loaded.",
  });
  const showBoundingBox = settings.showBoundingBox;
  const isLiveChartsCollapsed = settings.collapseLiveCharts;
  const isStepImportCollapsed = settings.collapseStepImport;
  const isTrajectoryCollapsed = settings.collapseTrajectory;
  const isRobotControlCollapsed = settings.collapseRobotControl;
  const visualizerRef = useRef<ArmVisualizerHandle | null>(null);
  const normalizedApiHost = useMemo(() => normaliseApiHost(apiHost), [apiHost]);
  const normalisedVisionHost = useMemo(
    () => normaliseVisionHost(visionHost),
    [visionHost],
  );

  const updateSettings = useCallback(
    (partial: Partial<PersistedSettings>) => {
      setSettings((prev) => {
        return { ...prev, ...partial };
      });
    },
    [],
  );
  const visionStreamUrl = useMemo(
    () => `${normalisedVisionHost}/stream.mjpg`,
    [normalisedVisionHost],
  );
  const visualWaypoints =
    plannerPoints.length > 0
      ? plannerPoints
      : previewPlan?.waypoints ?? [];
  const visualPathPoints =
    previewPlan?.pathPoints && previewPlan.pathPoints.length > 0
      ? previewPlan.pathPoints
      : visualWaypoints;
  const toggleButtonClasses = useMemo(
    () =>
      isConnected
        ? "rounded-full bg-gradient-to-r from-rose-500 to-rose-600 p-2 text-white shadow-md shadow-rose-500/30 transition hover:brightness-110"
        : "rounded-full bg-gradient-to-r from-cyan-400 to-blue-500 p-2 text-slate-950 shadow-md shadow-blue-500/30 transition hover:brightness-110",
    [isConnected],
  );
  const cameraButtonClasses = useMemo(
    () =>
      isVisionActive
        ? "rounded-full bg-gradient-to-r from-rose-500 to-rose-600 p-2 text-white shadow-md shadow-rose-500/30 transition hover:brightness-110"
        : "rounded-full bg-gradient-to-r from-cyan-400 to-blue-500 p-2 text-slate-950 shadow-md shadow-blue-500/30 transition hover:brightness-110",
    [isVisionActive],
  );
  const eventSourceRef = useRef<EventSource | null>(null);
  const trajectoryRefreshInFlight = useRef(false);

  const disconnect = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setIsConnected(false);
    setLatest(null);
    setIsVisionActive(false);
    setVisionError(null);
    setPreviewPlan(null);
    setPlannerPoints([]);
    setIsPlanning(false);
    setIsPlanLoading(false);
    setIsRunningPreview(false);
    setSavedTrajectories([]);
    setIsTrajectoryListLoading(false);
    setSelectedTrajectory("");
    setIsLoadingSavedTrajectory(false);
    setIsHoming(false);
  }, []);

  const handleMessage = useCallback((payload: string) => {
    let joints: number[] | undefined;
    let gripper: number | undefined;
    let servos: Record<string, ServoSample> | undefined;
    let parsedAlerts: Alert[] | undefined;

    try {
      const parsed = JSON.parse(payload);
      if (Array.isArray(parsed?.joints)) {
        joints = parsed.joints
          .map((value: unknown) =>
            typeof value === "number" ? value : Number(value),
          )
          .filter((value: number) => Number.isFinite(value));
      }
      if (typeof parsed?.gripper === "number") {
        gripper = parsed.gripper;
      }
      if (parsed && typeof parsed === "object" && parsed.servos && typeof parsed.servos === "object") {
        const out: Record<string, ServoSample> = {};
        for (const [k, v] of Object.entries(parsed.servos as Record<string, unknown>)) {
          if (v && typeof v === "object") {
            const s = v as Record<string, unknown>;
            const sample: ServoSample = {};
            if (typeof s.voltage_v === "number") sample.voltage_v = s.voltage_v;
            if (typeof s.temp_c === "number") sample.temp_c = s.temp_c;
            if (typeof s.current_a === "number") sample.current_a = s.current_a;
            if (typeof s.drive_duty_per_mille === "number") sample.drive_duty_per_mille = s.drive_duty_per_mille;
            if (typeof s.unloading_condition === "number") sample.unloading_condition = s.unloading_condition;
            if (typeof s.led_alarm_condition === "number") sample.led_alarm_condition = s.led_alarm_condition;
            if (typeof s.unloading_bits === "string") sample.unloading_bits = s.unloading_bits;
            if (typeof s.led_alarm_bits === "string") sample.led_alarm_bits = s.led_alarm_bits;
            out[k] = sample;
          }
        }
        servos = out;
      }
      // Alerts (optional)
      if (parsed && typeof parsed === "object") {
        const maybeObj = parsed as Record<string, unknown>;
        if (Array.isArray(maybeObj.alerts)) {
          parsedAlerts = maybeObj.alerts as Alert[];
        }
      }
    } catch {
      // fall back to raw payload only
    }

    const next: TelemetryEvent = {
      timestamp: Date.now(),
      raw: payload,
      joints,
      gripper,
      servos,
      alerts: parsedAlerts,
    };
    setLatest(next);
    // Merge alerts into state (keep last 20)
    if (Array.isArray(next.alerts) && next.alerts.length > 0) {
      setAlerts((prev) => {
        const merged = [...prev, ...next.alerts!];
        return merged.slice(-20);
      });
    }
  }, []);

  const connect = useCallback(() => {
    if (isConnected) {
      return;
    }
    const host = normalizedApiHost;
    const url = `${host}/monitor`;
    setError(null);

    try {
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        setLatest(null);
      };

      es.onerror = () => {
        setError(
          "Connection lost. Ensure the API is reachable and CORS allows this origin.",
        );
        disconnect();
      };

      es.onmessage = (evt) => {
        handleMessage(evt.data);
      };
    } catch (err) {
      setError((err as Error).message);
      disconnect();
    }
  }, [disconnect, handleMessage, isConnected, normalizedApiHost]);

  const toggleConnection = useCallback(() => {
    if (isConnected) {
      disconnect();
      return;
    }
    connect();
  }, [connect, disconnect, isConnected]);

  const toggleVision = useCallback(() => {
    if (isVisionActive) {
      setIsVisionActive(false);
      setVisionError(null);
      return;
    }
    setVisionError(null);
    setIsVisionActive(true);
  }, [isVisionActive]);

  const handleResetView = useCallback(() => {
    visualizerRef.current?.resetView();
  }, []);

  const handleStepFileChange = useCallback((file: File | null) => {
    setStepFile(file);
    if (file) {
      setStepTransform(DEFAULT_STEP_TRANSFORM);
    }
  }, []);

  const handleClearStepFile = useCallback(() => {
    setStepFile(null);
    setStepLoadStatus({ state: "idle", message: "No STEP model loaded." });
  }, []);

  const handleStepTransformChange = useCallback(
    (
      group: "position" | "rotationDeg",
      axis: "x" | "y" | "z",
      value: number,
    ) => {
      setStepTransform((current) => ({
        ...current,
        [group]: {
          ...current[group],
          [axis]: value,
        },
      }));
    },
    [],
  );

  const handleStepScaleChange = useCallback((value: number) => {
    setStepTransform((current) => ({
      ...current,
      scale: Number.isFinite(value) ? Math.max(0.01, value) : current.scale,
    }));
  }, []);

  const handleResetStepTransform = useCallback(() => {
    setStepTransform(DEFAULT_STEP_TRANSFORM);
  }, []);

  const requestPlannerPreview = useCallback(
    async (points: Point3[]) => {
      if (points.length === 0) {
        setPreviewPlan(null);
        setPlannerPoints([]);
        return;
      }
      setIsPlanLoading(true);
      setError(null);
      try {
        const response = await fetch(`${normalizedApiHost}/trajectory/plan-points`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ points: encodePointsForApi(points) }),
        });
        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || `Plan request failed (${response.status})`);
        }
        const data = await response.json();
        const { plan, waypoints } = previewFromPlannerPayload(data);
        setPreviewPlan(plan);
        setPlannerPoints(waypoints);
      } catch (err) {
        setError(`Failed to plan trajectory: ${(err as Error).message}`);
      } finally {
        setIsPlanLoading(false);
      }
    },
    [normalizedApiHost],
  );

  const handlePlanToggle = useCallback(() => {
    if (isPlanLoading || isRunningPreview) {
      return;
    }
    setError(null);
    setIsPlanning((current) => {
      const next = !current;
      if (next) {
        setPlannerPoints((existing) =>
          existing.length > 0
            ? existing
            : previewPlan?.waypoints ?? [],
        );
      }
      return next;
    });
  }, [isPlanLoading, isRunningPreview, previewPlan]);

  const handlePointSelected = useCallback(
    async (point: Point3) => {
      if (!isPlanning || isPlanLoading) {
        return;
      }
      const nextPoints = [...plannerPoints, point];
      setPlannerPoints(nextPoints);
      await requestPlannerPreview(nextPoints);
    },
    [isPlanning, isPlanLoading, plannerPoints, requestPlannerPreview],
  );

  const handleUndoPoint = useCallback(async () => {
    if (plannerPoints.length === 0 || isPlanLoading) {
      return;
    }
    const nextPoints = plannerPoints.slice(0, -1);
    setPlannerPoints(nextPoints);
    if (nextPoints.length === 0) {
      setPreviewPlan(null);
      return;
    }
    await requestPlannerPreview(nextPoints);
  }, [plannerPoints, isPlanLoading, requestPlannerPreview]);

  const handleRunPreview = useCallback(async () => {
    if (!previewPlan || isPlanLoading || isRunningPreview) {
      return;
    }
    setIsRunningPreview(true);
    setError(null);
    try {
      const response = await fetch(`${normalizedApiHost}/trajectory/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: previewPlan.name, use_cache: true }),
      });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Run request failed (${response.status})`);
      }
    } catch (err) {
      setError(`Failed to execute trajectory: ${(err as Error).message}`);
    } finally {
      setIsRunningPreview(false);
    }
  }, [previewPlan, isPlanLoading, isRunningPreview, normalizedApiHost]);

  const handleClearPreview = useCallback(() => {
    setError(null);
    setPreviewPlan(null);
    setPlannerPoints([]);
    setIsPlanning(false);
  }, []);

  const refreshTrajectoryList = useCallback(async () => {
    if (trajectoryRefreshInFlight.current) {
      return;
    }
    trajectoryRefreshInFlight.current = true;
    setError(null);
    setIsTrajectoryListLoading(true);
    try {
      const response = await fetch(`${normalizedApiHost}/trajectory/list`);
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `List request failed (${response.status})`);
      }
      const data = (await response.json()) as { trajectories?: unknown };
      const names = Array.isArray(data.trajectories)
        ? data.trajectories
            .map((value) =>
              typeof value === "string" ? value.trim() : "",
            )
            .filter((value): value is string => value.length > 0)
        : [];
      setSavedTrajectories(names);
      setSelectedTrajectory((current) =>
        current && names.includes(current) ? current : names[0] ?? "",
      );
    } catch (err) {
      setError(`Failed to load trajectories: ${(err as Error).message}`);
      setSavedTrajectories([]);
      setSelectedTrajectory("");
    } finally {
      setIsTrajectoryListLoading(false);
      trajectoryRefreshInFlight.current = false;
    }
  }, [normalizedApiHost]);

  const handleSelectTrajectory = useCallback((value: string) => {
    setSelectedTrajectory(value);
  }, []);

  const handleLoadTrajectory = useCallback(async () => {
    if (!selectedTrajectory || isLoadingSavedTrajectory) {
      return;
    }
    setError(null);
    setIsLoadingSavedTrajectory(true);
    try {
      const response = await fetch(
        `${normalizedApiHost}/trajectory/detail/${encodeURIComponent(selectedTrajectory)}`,
      );
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Load request failed (${response.status})`);
      }
      const data = await response.json();
      const plan = previewFromTrajectoryDetail(
        typeof data?.name === "string" ? data.name : selectedTrajectory,
        data?.trajectory ?? { moves: [] },
      );
      setPreviewPlan(plan);
      setPlannerPoints(plan.waypoints);
      setIsPlanning(false);
    } catch (err) {
      setError(`Failed to load trajectory: ${(err as Error).message}`);
    } finally {
      setIsLoadingSavedTrajectory(false);
    }
  }, [selectedTrajectory, isLoadingSavedTrajectory, normalizedApiHost]);

  const issueStop = useCallback(async () => {
    if (isStopping) {
      return;
    }
    const stopEndpoint = `${normalizedApiHost}/control/stop`;
    setIsStopping(true);
    try {
      const response = await fetch(stopEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try {
          const parsed = await response.json();
          if (typeof parsed?.detail === "string") {
            detail = parsed.detail;
          }
        } catch {
          // ignore parse error, keep default detail
        }
        throw new Error(detail);
      }
    } catch (err) {
      setError(
        `Failed to send STOP command: ${(err as Error).message ?? "Unknown error"}`,
      );
    } finally {
      setIsStopping(false);
    }
  }, [isStopping, normalizedApiHost]);

  const handleHome = useCallback(async () => {
    if (isHoming) {
      return;
    }
    setError(null);
    setIsHoming(true);
    try {
      const response = await fetch(`${normalizedApiHost}/control/home`, {
        method: "POST",
      });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Home request failed (${response.status})`);
      }
    } catch (err) {
      setError(`Failed to home: ${(err as Error).message ?? "Unknown error"}`);
    } finally {
      setIsHoming(false);
    }
  }, [isHoming, normalizedApiHost]);

  const handleRest = useCallback(async () => {
    if (isResting) {
      return;
    }
    setError(null);
    setIsResting(true);
    try {
      const response = await fetch(`${normalizedApiHost}/control/rest`, {
        method: "POST",
      });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Rest request failed (${response.status})`);
      }
    } catch (err) {
      setError(`Failed to move to rest: ${(err as Error).message ?? "Unknown error"}`);
    } finally {
      setIsResting(false);
    }
  }, [isResting, normalizedApiHost]);

  useEffect(() => {
    if (!hasAttemptedAutoConnect) {
      setHasAttemptedAutoConnect(true);
      connect();
    }
  }, [connect, hasAttemptedAutoConnect]);

  useEffect(() => {
    if (!isConnected) {
      return;
    }
    refreshTrajectoryList();
  }, [isConnected, refreshTrajectoryList]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  useEffect(() => {
    if (isConnected) {
      setIsVisionActive(true);
    } else {
      setIsVisionActive(false);
    }
  }, [isConnected]);

  useEffect(() => {
    setVisionError(null);
  }, [normalisedVisionHost]);

  // Lightweight API health probe to surface clearer 5xx reasons
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await fetch(`${normalizedApiHost}/health`, { method: "GET" });
        if (!r.ok) {
          const txt = await r.text();
          if (!cancelled) {
            setError(`API /health ${r.status}: ${txt || r.statusText}`);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError("API unreachable. Check that gradient-api is running.");
        }
      }
    };
    const id = window.setInterval(tick, 5000);
    tick(); // immediate first probe
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [normalizedApiHost]);
  useEffect(() => {
    persistSettings(settings);
  }, [settings]);

  const streamingLabel = useMemo(
    () => (isConnected ? "Streaming" : "Disconnected"),
    [isConnected],
  );
  const headerAlert = [error, visionError].filter(Boolean).join(" • ");
  const hasHeaderAlert = headerAlert.length > 0;
  const alertTone = error ? "rose" : "amber";

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-slate-900/80 via-slate-950 to-black text-slate-100">
      <header className="relative flex flex-col gap-4 border-b border-slate-800/40 bg-slate-950/60 px-6 py-6 shadow-inner shadow-slate-900/40 backdrop-blur">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col shrink-0">
            <div className="flex justify-end text-2xl font-semibold tracking-tight text-cyan-300 sm:text-3xl w-full">
              Control Center
            </div>
            <div className="flex justify-end text-md tracking-tight text-cyan-300 sm:text-md w-full">
              Gradient Robotics
            </div>
          </div>
          <div className="flex min-w-0 flex-1 items-center sm:px-4">
            <div
              className={`flex h-10 w-full items-center overflow-hidden rounded-lg border px-3 text-xs sm:text-sm ${
                hasHeaderAlert
                  ? alertTone === "rose"
                    ? "border-rose-500/40 bg-rose-500/10 text-rose-200"
                    : "border-amber-500/40 bg-amber-500/10 text-amber-200"
                  : "border-transparent bg-transparent text-transparent"
              }`}
              role={hasHeaderAlert ? "alert" : undefined}
              aria-live={hasHeaderAlert ? "polite" : undefined}
              aria-hidden={!hasHeaderAlert}
              title={hasHeaderAlert ? headerAlert : undefined}
            >
              {hasHeaderAlert && <span className="w-full truncate">{headerAlert}</span>}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
                isConnected
                  ? "bg-emerald-500/15 text-emerald-200 ring-1 ring-inset ring-emerald-400/30"
                  : "bg-rose-500/10 text-rose-200 ring-1 ring-inset ring-rose-400/20"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  isConnected ? "bg-emerald-400" : "bg-rose-400"
                }`}
              />
              {streamingLabel}
            </span>
            <button
              type="button"
              onClick={toggleConnection}
              className={toggleButtonClasses}
              aria-label={isConnected ? "Disconnect from robot" : "Connect to robot"}
            >
              {isConnected ? (
                <Unplug size={18} strokeWidth={2} />
              ) : (
                <Plug size={18} strokeWidth={2} />
              )}
            </button>
            <button
              type="button"
              onClick={handleHome}
              disabled={!isConnected || isHoming}
              className={`rounded-full border border-slate-600/60 bg-slate-900/60 p-2 text-slate-300 transition hover:border-slate-400 hover:text-slate-100 ${
                (!isConnected || isHoming) ? "opacity-60 cursor-not-allowed" : ""
              }`}
              aria-label="Move arm to home position"
            >
              <Home size={18} strokeWidth={2} />
            </button>
            <button
              type="button"
              onClick={handleRest}
              disabled={!isConnected || isResting}
              className={`rounded-full border border-slate-600/60 bg-slate-900/60 p-2 text-slate-300 transition hover:border-slate-400 hover:text-slate-100 ${
                (!isConnected || isResting) ? "opacity-60 cursor-not-allowed" : ""
              }`}
              aria-label="Move arm to rest pose"
            >
              <Moon size={18} strokeWidth={2} />
            </button>
            <button
              type="button"
              onClick={issueStop}
              disabled={isStopping}
              className={`rounded-full bg-gradient-to-r from-rose-600 to-rose-700 p-2 text-white shadow-md shadow-rose-500/40 transition ${
                isStopping ? "cursor-wait opacity-60" : "hover:brightness-110"
              }`}
              aria-label="Send emergency stop"
            >
              <Octagon size={18} strokeWidth={2.5} />
            </button>
            <button
              type="button"
              onClick={toggleVision}
              className={cameraButtonClasses}
              aria-label={isVisionActive ? "Disable camera overlay" : "Enable camera overlay"}
            >
              {isVisionActive ? (
                <Camera size={18} strokeWidth={2} />
              ) : (
                <CameraOff size={18} strokeWidth={2} />
              )}
            </button>
            <button
              type="button"
              onClick={handleResetView}
              className="rounded-full border border-slate-600/60 bg-slate-900/60 p-2 text-slate-300 transition hover:border-slate-400 hover:text-slate-100"
              aria-label="Reset arm view"
            >
              <RefreshCcw size={18} strokeWidth={2} />
            </button>
            <button
              type="button"
              onClick={() => setIsSettingsOpen(true)}
              className="rounded-full border border-slate-600/60 bg-slate-900/60 p-2 text-slate-300 transition hover:border-slate-400 hover:text-slate-100"
              aria-label="Open settings"
            >
              <Settings size={18} strokeWidth={2} />
            </button>
          </div>
        </div>
      </header>
      <main className="relative flex-1 overflow-hidden">
        <ArmVisualizer
          ref={visualizerRef}
          joints={latest?.joints}
          showBoundingBox={showBoundingBox}
          selectionMode={isPlanning && !isPlanLoading}
          onPointSelected={handlePointSelected}
          pathPoints={visualPathPoints}
          waypoints={visualWaypoints}
          stepFile={stepFile}
          stepTransform={stepTransform}
          onStepStatusChange={setStepLoadStatus}
        />
        <div className="pointer-events-auto absolute left-6 top-6 z-10 flex max-w-sm flex-col gap-2">
          {isVisionActive && !visionError && (
            <div className="overflow-hidden rounded-xl border border-slate-700/60 bg-slate-950/80 shadow-lg shadow-slate-950/40 backdrop-blur">
              <img
                src={visionStreamUrl}
                alt="Gradient Vision stream"
                className="block max-h-64 w-full object-cover"
                onLoad={() => setVisionError(null)}
                onError={() => {
                  setVisionError(
                    "Unable to load the vision stream. Ensure Gradient Vision is running and accessible.",
                  );
                  setIsVisionActive(false);
                }}
              />
            </div>
          )}
          <CollapsibleOverlayPanel
            title="Live Charts"
            collapsed={isLiveChartsCollapsed}
            onToggle={() =>
              updateSettings({ collapseLiveCharts: !isLiveChartsCollapsed })
            }
            widthClassName="w-full max-w-xl"
          >
            <TelemetryCharts latest={latest} />
          </CollapsibleOverlayPanel>
        </div>
        <div className="pointer-events-none absolute left-1/2 top-4 z-20 -translate-x-1/2 transform">
          <AlertsPanel
            alerts={alerts}
            onDismiss={(idx) =>
              setAlerts((prev) => {
                const copy = [...prev];
                copy.splice(idx, 1);
                return copy;
              })
            }
          />
        </div>
        <div className="pointer-events-none absolute right-6 top-6 z-10 flex flex-col gap-3">
          <CollapsibleOverlayPanel
            title="STEP Import"
            collapsed={isStepImportCollapsed}
            onToggle={() =>
              updateSettings({ collapseStepImport: !isStepImportCollapsed })
            }
          >
            <StepImportPanel
              stepFileName={stepFile?.name ?? null}
              stepStatus={stepLoadStatus}
              transform={stepTransform}
              onFileChange={handleStepFileChange}
              onTransformChange={handleStepTransformChange}
              onScaleChange={handleStepScaleChange}
              onResetTransform={handleResetStepTransform}
              onClearFile={handleClearStepFile}
            />
          </CollapsibleOverlayPanel>
          <CollapsibleOverlayPanel
            title="Trajectory"
            collapsed={isTrajectoryCollapsed}
            onToggle={() =>
              updateSettings({ collapseTrajectory: !isTrajectoryCollapsed })
            }
          >
            <TrajectoryPanel
              isPlanning={isPlanning}
              isPlanLoading={isPlanLoading}
              isRunning={isRunningPreview}
              preview={previewPlan}
              plannerPoints={plannerPoints}
              savedTrajectories={savedTrajectories}
              selectedTrajectory={selectedTrajectory}
              isTrajectoryListLoading={isTrajectoryListLoading}
              isLoadingSavedTrajectory={isLoadingSavedTrajectory}
              onPlanToggle={handlePlanToggle}
              onRun={handleRunPreview}
              onClear={handleClearPreview}
              onRefreshTrajectories={refreshTrajectoryList}
              onSelectTrajectory={handleSelectTrajectory}
              onLoadTrajectory={handleLoadTrajectory}
              onUndoPoint={handleUndoPoint}
            />
          </CollapsibleOverlayPanel>
        </div>
        <div className="pointer-events-none absolute right-6 bottom-6 z-20">
          <CollapsibleOverlayPanel
            title="Robot Control"
            collapsed={isRobotControlCollapsed}
            onToggle={() =>
              updateSettings({ collapseRobotControl: !isRobotControlCollapsed })
            }
            widthClassName="w-[360px]"
          >
            <ControlPanel apiHost={normalizedApiHost} onError={(m) => setError(m)} />
          </CollapsibleOverlayPanel>
        </div>
      </main>
      <SettingsDialog
        isOpen={isSettingsOpen}
        apiHost={apiHost}
        visionHost={visionHost}
        showBoundingBox={showBoundingBox}
        onHostChange={setApiHost}
        onVisionHostChange={setVisionHost}
        onShowBoundingBoxChange={(value) => updateSettings({ showBoundingBox: value })}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}
