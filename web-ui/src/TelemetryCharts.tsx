import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";

type ServoSample = {
  voltage_v?: number;
  temp_c?: number;
  current_a?: number;
  drive_duty_per_mille?: number;
  led_alarm_bits?: string;
  unloading_bits?: string;
  led_alarm_names?: string[];       // optional, if backend provides names
  unloading_names?: string[];       // optional, if backend provides names
  status_bits?: string;             // optional, live status bits "b0,b3"
  status_names?: string[];          // optional, live status names
};

export type TelemetryEvent = {
  timestamp: number;
  joints?: number[];
  servos?: Record<string, ServoSample>;
};

function MiniChart({
  title,
  data,
  color = "#22d3ee",
  unit,
  min,
  max,
  width,
  height,
}: {
  title: string;
  data: number[];
  color?: string;
  unit?: string;
  min?: number;
  max?: number;
  width?: number;
  height?: number;
}) {
  const w = Math.max(140, Math.floor((typeof width === "number" ? width : 220)));
  const h = typeof height === "number" ? height : 60;
  // Extra inner padding so the stroke never touches the edges (symmetric)
  const padX = 16;
  const padY = 12;
  const path = useMemo(() => {
    if (data.length < 2) return "";
    const xmin = 0;
    const xmax = Math.max(1, data.length - 1);
    const datMin = min ?? Math.min(...data);
    const datMax = max ?? Math.max(...data);
    const span = datMax - datMin || 1;

    // Center first and last samples away from edges by half-step (symmetric)
    const count = data.length;
    const dx = (w - padX * 2) / Math.max(2, count + 1);
    const sx = (i: number) => padX + dx * (i + 1);
    const sy = (v: number) =>
      h - padY - ((v - datMin) / span) * (h - padY * 2);
    let d = `M ${sx(0)} ${sy(data[0])}`;
    for (let i = 1; i < data.length; i++) {
      d += ` L ${sx(i)} ${sy(data[i])}`;
    }
    return d;
  }, [data, min, max]);

  const latest = data.length ? data[data.length - 1] : undefined;
  return (
    <div className="rounded-lg border border-slate-700/60 bg-slate-950/70 p-3">
      <div className="mb-1 flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200/80">
          {title}
        </div>
        <div className="text-xs text-slate-300/80">
          {typeof latest === "number" ? `${latest.toFixed(2)}${unit ?? ""}` : "—"}
        </div>
      </div>
      <svg width={w} height={h} style={{ display: "block" }}>
        <rect
          x="0"
          y="0"
          width={w}
          height={h}
          rx="6"
          ry="6"
          fill="transparent"
        />
        <path d={path} stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>
    </div>
  );
}

function MultiChart({
  title,
  series,
  unit,
  width,
  height,
}: {
  title: string;
  series: Record<string, number[]>;
  unit?: string;
  width?: number;
  height?: number;
}) {
  const w = Math.max(140, Math.floor((typeof width === "number" ? width : 220)));
  const h = typeof height === "number" ? height : 60;
  const padX = 16;
  const padY = 12;
  const ids = Object.keys(series).sort();
  const allValues: number[] = [];
  ids.forEach((id) => allValues.push(...series[id]));
  const datMin = allValues.length ? Math.min(...allValues) : 0;
  const datMax = allValues.length ? Math.max(...allValues) : 1;
  const span = datMax - datMin || 1;
  const maxLen = ids.reduce((m, id) => Math.max(m, series[id].length), 0);
  const dxBase = (w - padX * 2) / Math.max(2, maxLen + 1);
  // Sequential palette (loops if there are more servos than colors)
  const palette = [
    "#22d3ee", "#38bdf8", "#60a5fa", "#818cf8", "#a78bfa", "#c084fc",
    "#f472b6", "#fb7185", "#f59e0b", "#84cc16", "#10b981", "#14b8a6",
    "#06b6d4", "#3b82f6", "#8b5cf6", "#d946ef",
  ];
  const idToColor: Record<string, string> = {};
  ids.forEach((id, idx) => {
    idToColor[id] = palette[idx % palette.length];
  });
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    index: number;
    items: { id: string; value: number; color: string }[];
  } | null>(null);
  const getIndexForX = (x: number) => {
    if (maxLen <= 1) return 0;
    const clampedX = Math.min(Math.max(x, padX), w - padX);
    const rawIndex = Math.round((clampedX - padX) / dxBase - 1);
    return Math.max(0, Math.min(maxLen - 1, rawIndex));
  };
  const buildItemsAtIndex = (globalIndex: number) => {
    const items: { id: string; value: number; color: string }[] = [];
    for (const id of ids) {
      const arr = series[id];
      if (!Array.isArray(arr) || arr.length === 0) continue;
      const offset = maxLen - arr.length;
      const localIndex = globalIndex - offset;
      if (localIndex < 0 || localIndex >= arr.length) continue;
      const value = arr[localIndex];
      if (typeof value === "number" && Number.isFinite(value)) {
        items.push({ id, value, color: idToColor[id] });
      }
    }
    // Sort numerically by servo id if possible
    items.sort((a, b) => Number(a.id) - Number(b.id));
    return items;
  };
  const updateTooltip = (e: MouseEvent<HTMLDivElement>) => {
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    let chartX = x;
    const svgRect = svgRef.current?.getBoundingClientRect();
    if (svgRect) chartX = e.clientX - svgRect.left;
    const index = getIndexForX(chartX);
    const items = buildItemsAtIndex(index);
    setTooltip({ x, y, index, items });
  };
  const paths = ids.map((id) => {
    const data = series[id];
    if (!data || data.length < 2) return null;
    const count = data.length;
    const dx = dxBase; // keep consistent spacing
    const sx = (i: number) => padX + dx * (i + (maxLen - count) + 1);
    const sy = (v: number) => h - padY - ((v - datMin) / span) * (h - padY * 2);
    let d = `M ${sx(0)} ${sy(data[0])}`;
    for (let i = 1; i < data.length; i++) d += ` L ${sx(i)} ${sy(data[i])}`;
    return { id, d, color: idToColor[id] };
  }).filter(Boolean) as { id: string; d: string; color: string }[];
  const latestVals = ids.map((id) => {
    const arr = series[id];
    return Array.isArray(arr) && arr.length ? arr[arr.length - 1] : undefined;
  }).filter((v): v is number => typeof v === "number");
  const latestVal = latestVals.length ? latestVals[latestVals.length - 1] : undefined;
  return (
    <div
      className="relative rounded-lg border border-slate-700/60 bg-slate-950/70 p-3"
      onMouseEnter={updateTooltip}
      onMouseMove={updateTooltip}
      onMouseLeave={() => setTooltip(null)}
    >
      <div className="mb-1 flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200/80">
          {title}
        </div>
        <div className="text-xs text-slate-300/80">
          {typeof latestVal === "number" ? `${latestVal.toFixed(2)}${unit ?? ""}` : "—"}
        </div>
      </div>
      <svg ref={svgRef} width={w} height={h} style={{ display: "block" }}>
        <rect x="0" y="0" width={w} height={h} rx="6" ry="6" fill="transparent" />
        {paths.map(({ id, d, color }) => (
          <path key={id} d={d} stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        ))}
      </svg>
      {tooltip && tooltip.items.length > 0 && (
        <div
          className="pointer-events-none absolute z-10 max-h-60 w-56 overflow-auto rounded-md border border-slate-600/60 bg-slate-900/95 p-2 text-xs text-slate-200 shadow-lg shadow-slate-900/70"
          style={{
            left: Math.min(Math.max(8, tooltip.x), w - 8),
            top: Math.max(8, tooltip.y - 8),
            transform: "translate(-50%,-100%)",
          }}
        >
          <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-400">
            {(() => {
              const samplesAgo = Math.max(0, maxLen - 1 - tooltip.index);
              return samplesAgo === 0 ? "Live per-servo" : `History (${samplesAgo} samples ago)`;
            })()}
          </div>
          <table className="w-full border-separate border-spacing-y-1">
            <tbody>
              {tooltip.items.map(({ id, value, color }) => (
                <tr key={`tip-${id}`}>
                  <td className="pr-3">
                    <span className="flex items-center gap-1">
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-slate-300">ID {id}</span>
                    </span>
                  </td>
                  <td className="text-right">
                    <span className="tabular-nums text-slate-100">
                      {value.toFixed(2)}{unit ?? ""}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function TelemetryCharts({ latest }: { latest: TelemetryEvent | null }) {
  const maxPoints = 300;
  const [jointsDeg, setJointsDeg] = useState<number[][]>([[], [], [], [], [], []]);
  const [voltagePerId, setVoltagePerId] = useState<Record<string, number[]>>({});
  const [currentPerId, setCurrentPerId] = useState<Record<string, number[]>>({});
  const [dutyPerId, setDutyPerId] = useState<Record<string, number[]>>({});
  const [tempPerId, setTempPerId] = useState<Record<string, number[]>>({});
  const [alarmSummary, setAlarmSummary] = useState<{ led: Set<number>; unload: Set<number> }>({
    led: new Set(),
    unload: new Set(),
  });
  const [activeAlarmToIds, setActiveAlarmToIds] = useState<Record<string, string[]>>({});
  const [ledAlarmToIds, setLedAlarmToIds] = useState<Record<string, string[]>>({});
  const [unloadAlarmToIds, setUnloadAlarmToIds] = useState<Record<string, string[]>>({});
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState<number>(240);
  const hasServos = !!latest?.servos && Object.keys(latest.servos).length > 0;
  const initedRef = useRef(false);

  // Measure container width to make charts responsive
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w && Number.isFinite(w)) setWidth(w);
      }
    });
    ro.observe(el);
    setWidth(el.clientWidth || 240);
    return () => {
      ro.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!latest) return;
    // Joints (radians -> degrees)
    if (Array.isArray(latest.joints) && latest.joints.length > 0) {
      setJointsDeg((prev) => {
        const next = [...prev.map((arr) => [...arr])];
        for (let i = 0; i < 6; i++) {
          const valRad = latest.joints?.[i];
          const valDeg =
            typeof valRad === "number" ? (valRad * 180) / Math.PI : undefined;
          if (typeof valDeg === "number") {
            const arr = next[i] ?? [];
            arr.push(valDeg);
            if (arr.length > maxPoints) arr.shift();
            next[i] = arr;
          }
        }
        return next as number[][];
      });
    }

    // Servo per-ID histories + alarms
    if (hasServos) {
      // Histories
      setVoltagePerId((prev) => {
        const next: Record<string, number[]> = { ...prev };
        for (const [sid, s] of Object.entries(latest!.servos!)) {
          if (typeof s.voltage_v === "number") {
            const arr = (next[sid] ?? []).slice();
            arr.push(s.voltage_v);
            if (arr.length > maxPoints) arr.shift();
            next[sid] = arr;
          }
        }
        return next;
      });
      setCurrentPerId((prev) => {
        const next: Record<string, number[]> = { ...prev };
        for (const [sid, s] of Object.entries(latest!.servos!)) {
          if (typeof s.current_a === "number") {
            const arr = (next[sid] ?? []).slice();
            arr.push(s.current_a);
            if (arr.length > maxPoints) arr.shift();
            next[sid] = arr;
          }
        }
        return next;
      });
      setDutyPerId((prev) => {
        const next: Record<string, number[]> = { ...prev };
        for (const [sid, s] of Object.entries(latest!.servos!)) {
          if (typeof s.drive_duty_per_mille === "number") {
            const arr = (next[sid] ?? []).slice();
            // Convert per-mille (‰) to percent (%)
            const percent = s.drive_duty_per_mille / 10.0;
            arr.push(percent);
            if (arr.length > maxPoints) arr.shift();
            next[sid] = arr;
          }
        }
        return next;
      });
      setTempPerId((prev) => {
        const next: Record<string, number[]> = { ...prev };
        for (const [sid, s] of Object.entries(latest!.servos!)) {
          if (typeof s.temp_c === "number") {
            const arr = (next[sid] ?? []).slice();
            arr.push(s.temp_c);
            if (arr.length > maxPoints) arr.shift();
            next[sid] = arr;
          }
        }
        return next;
      });
      const activeBits = new Set<number>();
      const ledBits = new Set<number>();
      const unloadBits = new Set<number>();
      const nextActiveMap: Record<string, Set<string>> = {};
      const nextLedMap: Record<string, Set<string>> = {};
      const nextUnloadMap: Record<string, Set<string>> = {};
      for (const [sid, s] of Object.entries(latest!.servos!)) {
        // Live status alarms preferred
        const statusNamesArr = Array.isArray(s.status_names) ? s.status_names : undefined;
        if (statusNamesArr && statusNamesArr.length > 0) {
          for (const name of statusNamesArr) {
            if (!nextActiveMap[name]) nextActiveMap[name] = new Set();
            nextActiveMap[name].add(sid);
          }
        } else if (typeof s.status_bits === "string" && s.status_bits.length > 0) {
          for (const tok of s.status_bits.split(",")) {
            const idx = Number(tok.replace(/^b/i, "").trim());
            if (Number.isFinite(idx)) {
              activeBits.add(idx);
              const label = labelForLedBit(idx);
              if (!nextActiveMap[label]) nextActiveMap[label] = new Set();
              nextActiveMap[label].add(sid);
            }
          }
        }
        // Gather LED alarm names if provided, else fall back to bits -> names
        const ledNamesArr = Array.isArray(s.led_alarm_names) ? s.led_alarm_names : undefined;
        const unloadNamesArr = Array.isArray(s.unloading_names) ? s.unloading_names : undefined;
        // LED alarms
        if (ledNamesArr && ledNamesArr.length > 0) {
          for (const name of ledNamesArr) {
            if (!nextLedMap[name]) nextLedMap[name] = new Set();
            nextLedMap[name].add(sid);
          }
        } else if (typeof s.led_alarm_bits === "string" && s.led_alarm_bits.length > 0) {
          for (const tok of s.led_alarm_bits.split(",")) {
            const idx = Number(tok.replace(/^b/i, "").trim());
            if (Number.isFinite(idx)) {
              ledBits.add(idx);
              const label = labelForLedBit(idx);
              if (!nextLedMap[label]) nextLedMap[label] = new Set();
              nextLedMap[label].add(sid);
            }
          }
        }
        // Unloading alarms
        if (unloadNamesArr && unloadNamesArr.length > 0) {
          for (const name of unloadNamesArr) {
            if (!nextUnloadMap[name]) nextUnloadMap[name] = new Set();
            nextUnloadMap[name].add(sid);
          }
        } else if (typeof s.unloading_bits === "string" && s.unloading_bits.length > 0) {
          for (const tok of s.unloading_bits.split(",")) {
            const idx = Number(tok.replace(/^b/i, "").trim());
            if (Number.isFinite(idx)) {
              unloadBits.add(idx);
              const label = labelForUnloadBit(idx);
              if (!nextUnloadMap[label]) nextUnloadMap[label] = new Set();
              nextUnloadMap[label].add(sid);
            }
          }
        }
      }
      // done histories
      // Finalize label -> ids map (sorted)
      const activeMapFinal: Record<string, string[]> = {};
      for (const [label, set] of Object.entries(nextActiveMap)) {
        activeMapFinal[label] = [...set].sort();
      }
      const ledMapFinal: Record<string, string[]> = {};
      for (const [label, set] of Object.entries(nextLedMap)) {
        ledMapFinal[label] = [...set].sort();
      }
      const unloadMapFinal: Record<string, string[]> = {};
      for (const [label, set] of Object.entries(nextUnloadMap)) {
        unloadMapFinal[label] = [...set].sort();
      }
      setActiveAlarmToIds(activeMapFinal);
      setLedAlarmToIds(ledMapFinal);
      setUnloadAlarmToIds(unloadMapFinal);
      setAlarmSummary({ led: ledBits, unload: unloadBits });
    } else if (!initedRef.current) {
      // Avoid flicker on first mount when servos not present
      initedRef.current = true;
    }
  }, [latest, hasServos]);

  const labelForLedBit = (b: number) => {
    const labels: Record<number, string> = {
      0: "Overload",
      1: "Overheat",
      2: "Overvoltage",
      3: "Undervoltage",
      4: "Stall",
      5: "Position Fault",
      6: "Comm/Error",
      7: "Unknown",
    };
    return labels[b] ?? `b${b}`;
  };
  const labelForUnloadBit = (b: number) => labelForLedBit(b);

  const halfWidth = Math.max(100, Math.floor((width - 8) / 2)); // 8px approximate gap

  return (
    <div ref={containerRef} className="pointer-events-auto w-full max-w-xl rounded-xl border border-slate-700/60 bg-slate-900/80 p-3 shadow-lg shadow-slate-900/50 backdrop-blur-lg">
      <div className="mb-2 text-xs font-semibold uppercase tracking-[0.25em] text-cyan-200/80">
        Live Charts
      </div>
      <div className="grid grid-cols-2 gap-2">
        <MiniChart title="J1 (deg)" data={jointsDeg[0]} color="#22d3ee" unit="" width={halfWidth} />
        <MiniChart title="J2 (deg)" data={jointsDeg[1]} color="#38bdf8" unit="" width={halfWidth} />
        <MiniChart title="J3 (deg)" data={jointsDeg[2]} color="#60a5fa" unit="" width={halfWidth} />
        <MiniChart title="J4 (deg)" data={jointsDeg[3]} color="#818cf8" unit="" width={halfWidth} />
        <MiniChart title="J5 (deg)" data={jointsDeg[4]} color="#a78bfa" unit="" width={halfWidth} />
        <MiniChart title="J6 (deg)" data={jointsDeg[5]} color="#c084fc" unit="" width={halfWidth} />
        <MultiChart title="Voltage (V)" series={voltagePerId} unit="V" width={halfWidth} />
        <MultiChart title="Current (A)" series={currentPerId} unit="A" width={halfWidth} />
        <MultiChart title="Torque/Load (%)" series={dutyPerId} unit="%" width={halfWidth} />
        <MultiChart title="Temp (°C)" series={tempPerId} unit="°C" width={halfWidth} />
        {Object.keys(activeAlarmToIds).length > 0 && (
          <div className="col-span-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-200">
            <div className="mb-1 font-semibold tracking-wider">Active Alarms</div>
            <div>
              {Object.entries(activeAlarmToIds).sort(([a], [b]) => a.localeCompare(b)).map(([name, ids]) => (
                <span key={`act-${name}`} className="mr-1 inline-block rounded bg-amber-400/20 px-1 py-0.5 text-amber-200">
                  {name}{ids.length ? `: ${ids.join(",")}` : ""}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


