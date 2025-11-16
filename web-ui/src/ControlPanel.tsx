import { useCallback, useMemo, useRef, useState } from "react";
import { DEFAULT_SPEED_SLIDER } from "./uiConstants";

type Props = {
	apiHost: string;
	onError?: (message: string) => void;
};

function expSliderToMultiplier(v: number): number {
	// v in [0..1000] → 10^((t*2)-1) with t=v/1000
	const t = Math.max(0, Math.min(1000, v)) / 1000;
	const expVal = (t * 2) - 1;
	let mult = Math.pow(10, expVal);
	if (mult < 0.1) mult = 0.1;
	if (mult > 10) mult = 10;
	return mult;
}

export function ControlPanel({ apiHost, onError }: Props) {
	const [speedVal, setSpeedVal] = useState<number>(DEFAULT_SPEED_SLIDER); // 0..1000
	const speedMult = useMemo(() => expSliderToMultiplier(speedVal), [speedVal]);
	const [grip, setGrip] = useState<number>(0);
	const gripTimerRef = useRef<number | null>(null);
	const [busy, setBusy] = useState<boolean>(false);
	// Realtime jog state
	const [jogEnabled, setJogEnabled] = useState<boolean>(false);
	const [deadman, setDeadman] = useState<boolean>(true);
	const [linBaseMmS, setLinBaseMmS] = useState<number>(50);
	const [angBaseDegS, setAngBaseDegS] = useState<number>(15);
	const jogTimerRef = useRef<number | null>(null);
	const lastSentRef = useRef<[number, number, number, number, number, number]>([0, 0, 0, 0, 0, 0]);
	const lastSentAtRef = useRef<number>(0);
	const keepaliveMs = 200;
	const linCountsRef = useRef<{ x: number; y: number; z: number }>({ x: 0, y: 0, z: 0 });
	const angCountsRef = useRef<{ x: number; y: number; z: number }>({ x: 0, y: 0, z: 0 });

	const post = useCallback(async (path: string, body?: unknown) => {
		try {
			const res = await fetch(`${apiHost}${path}`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: body ? JSON.stringify(body) : undefined,
			});
			if (!res.ok) {
				const msg = await res.text();
				throw new Error(msg || `${res.status} ${res.statusText}`);
			}
		} catch (err) {
			const msg = (err as Error)?.message || "request failed";
			console.error("ControlPanel error:", err);
			try {
				onError?.(msg);
			} catch {
				// ignore
			}
		}
	}, [apiHost]);

	const handleGripChange = useCallback((value: number) => {
		setGrip(value);
		if (gripTimerRef.current) {
			window.clearTimeout(gripTimerRef.current);
			gripTimerRef.current = null;
		}
		gripTimerRef.current = window.setTimeout(async () => {
			gripTimerRef.current = null;
			await post("/control/set-gripper", { angle_deg: value });
		}, 80);
	}, [post]);

	// ------------------------
	// Realtime jog helpers
	// ------------------------
	const computeJogVector = useCallback(() => {
		const lc = linCountsRef.current;
		const ac = angCountsRef.current;
		const baseMS = (linBaseMmS / 1000.0) * speedMult;
		const baseDegS = angBaseDegS * speedMult;
		const vx = (lc.x > 0 ? 1 : lc.x < 0 ? -1 : 0) * baseMS;
		const vy = (lc.y > 0 ? 1 : lc.y < 0 ? -1 : 0) * baseMS;
		const vz = (lc.z > 0 ? 1 : lc.z < 0 ? -1 : 0) * baseMS;
		const vroll = (ac.x > 0 ? 1 : ac.x < 0 ? -1 : 0) * baseDegS;
		const vpitch = (ac.y > 0 ? 1 : ac.y < 0 ? -1 : 0) * baseDegS;
		const vyaw = (ac.z > 0 ? 1 : ac.z < 0 ? -1 : 0) * baseDegS;
		if (!deadman) return [0, 0, 0, 0, 0, 0] as [number, number, number, number, number, number];
		return [vx, vy, vz, vroll, vpitch, vyaw] as [number, number, number, number, number, number];
	}, [linBaseMmS, angBaseDegS, speedMult, deadman]);

	const sendJogTick = useCallback(async () => {
		const now = Date.now();
		const v = computeJogVector();
		const last = lastSentRef.current;
		const changed =
			v[0] !== last[0] || v[1] !== last[1] || v[2] !== last[2] ||
			v[3] !== last[3] || v[4] !== last[4] || v[5] !== last[5];
		if (!changed && now - lastSentAtRef.current < keepaliveMs) {
			return;
		}
		await post("/control/jog/velocity", {
			vx: Number(v[0].toFixed(6)),
			vy: Number(v[1].toFixed(6)),
			vz: Number(v[2].toFixed(6)),
			v_roll: Number(v[3].toFixed(3)),
			v_pitch: Number(v[4].toFixed(3)),
			v_yaw: Number(v[5].toFixed(3)),
		});
		lastSentRef.current = v;
		lastSentAtRef.current = now;
	}, [computeJogVector, post]);

	const ensureJogStarted = useCallback(async () => {
		if (!jogEnabled) {
			setJogEnabled(true);
			await post("/control/jog/start");
			await post("/control/jog/deadman", { enabled: deadman });
			// start timer
			if (jogTimerRef.current) {
				window.clearInterval(jogTimerRef.current);
			}
			jogTimerRef.current = window.setInterval(() => {
				sendJogTick().catch(() => {});
			}, 20);
		}
	}, [jogEnabled, post, deadman, sendJogTick]);

	const stopJog = useCallback(async () => {
		setJogEnabled(false);
		if (jogTimerRef.current) {
			window.clearInterval(jogTimerRef.current);
			jogTimerRef.current = null;
		}
		linCountsRef.current = { x: 0, y: 0, z: 0 };
		angCountsRef.current = { x: 0, y: 0, z: 0 };
		lastSentRef.current = [0, 0, 0, 0, 0, 0];
		await post("/control/jog/velocity", { vx: 0, vy: 0, vz: 0, v_roll: 0, v_pitch: 0, v_yaw: 0 });
		await post("/control/jog/stop");
	}, [post]);

	const onDeadmanToggle = useCallback(async (enabled: boolean) => {
		setDeadman(enabled);
		await post("/control/jog/deadman", { enabled });
	}, [post]);
	const onDebugToggle = useCallback(async (enabled: boolean) => {
		await post("/control/jog/debug", { enabled });
	}, [post]);

	const changeLinearCount = useCallback(async (axis: "x" | "y" | "z", delta: number) => {
		await ensureJogStarted();
		linCountsRef.current = { ...linCountsRef.current, [axis]: linCountsRef.current[axis] + delta };
		// immediate tick to avoid delay
		await sendJogTick();
	}, [ensureJogStarted, sendJogTick]);

	const changeAngularCount = useCallback(async (axis: "x" | "y" | "z", delta: number) => {
		await ensureJogStarted();
		angCountsRef.current = { ...angCountsRef.current, [axis]: angCountsRef.current[axis] + delta };
		await sendJogTick();
	}, [ensureJogStarted, sendJogTick]);

	const onPress = useCallback((fn: () => void) => (e: React.PointerEvent<HTMLButtonElement>) => {
		(e.currentTarget as HTMLButtonElement).setPointerCapture(e.pointerId);
		fn();
	}, []);
	const onRelease = useCallback((fn: () => void) => (e: React.PointerEvent<HTMLButtonElement>) => {
		try {
			(e.currentTarget as HTMLButtonElement).releasePointerCapture(e.pointerId);
		} catch {}
		fn();
	}, []);

	return (
		<div className="pointer-events-auto w-[360px] rounded-xl border border-slate-700/60 bg-slate-900/80 p-4 text-slate-100 shadow-lg shadow-slate-900/40 backdrop-blur">
			<div className="mb-2 text-xs font-semibold uppercase tracking-[0.25em] text-cyan-200/80">
				Robot Control
			</div>
			{/* Removed step move blocks; unified under realtime jog below */}
			<div className="mb-3 rounded-lg border border-slate-700/60 p-2">
				<div className="mb-2 flex items-center justify-between text-xs text-slate-300/80">
					<span className="font-semibold">Gripper</span>
					<span className="tabular-nums">{grip}°</span>
				</div>
				<input
					type="range"
					min={0}
					max={180}
					value={grip}
					onChange={(e) => handleGripChange(Number(e.target.value))}
					className="w-full accent-cyan-400"
				/>
				<div className="mt-1 flex gap-2">
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" onClick={() => handleGripChange(120)}>Open</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700" onClick={() => handleGripChange(0)}>Close</button>
				</div>
			</div>
			<div className="mb-3 rounded-lg border border-slate-700/60 p-2">
				<div className="mb-2 flex items-center justify-between text-xs text-slate-300/80">
					<span className="font-semibold">Speed Multiplier</span>
					<span className="tabular-nums">{speedMult.toFixed(2)}x</span>
				</div>
				<input
					type="range"
					min={0}
					max={1000}
					value={speedVal}
					onChange={(e) => setSpeedVal(Number(e.target.value))}
					className="w-full accent-cyan-400"
				/>
			</div>
			<div className="mb-3 rounded-lg border border-slate-700/60 p-2">
				<div className="mb-2 flex items-center justify-between text-xs text-slate-300/80">
					<span className="font-semibold">Realtime Jog</span>
					<div className="flex items-center gap-2">
						<label className="flex items-center gap-1 text-[12px]">
							<input type="checkbox" checked={deadman} onChange={(e) => onDeadmanToggle(e.target.checked)} />
							Deadman
						</label>
						<label className="flex items-center gap-1 text-[12px]">
							<input type="checkbox" onChange={(e) => onDebugToggle(e.target.checked)} />
							Debug
						</label>
						<button
							className={`rounded px-2 py-1 ${jogEnabled ? "bg-rose-600 text-white" : "bg-slate-800 hover:bg-slate-700"}`}
							onClick={async () => (jogEnabled ? await stopJog() : await ensureJogStarted())}
						>
							{jogEnabled ? "Stop" : "Start"}
						</button>
					</div>
				</div>
				<div className="mb-2 grid grid-cols-2 gap-2">
					<label className="flex items-center justify-between rounded border border-slate-700/60 bg-slate-800/60 px-2 py-1 text-xs">
						<span>Linear (mm/s)</span>
						<input
							className="w-16 rounded bg-slate-900/60 px-1 text-right outline-none"
							type="number"
							value={linBaseMmS}
							min={0}
							max={1000}
							onChange={(e) => setLinBaseMmS(Number(e.target.value))}
						/>
					</label>
					<label className="flex items-center justify-between rounded border border-slate-700/60 bg-slate-800/60 px-2 py-1 text-xs">
						<span>Angular (deg/s)</span>
						<input
							className="w-16 rounded bg-slate-900/60 px-1 text-right outline-none"
							type="number"
							value={angBaseDegS}
							min={0}
							max={360}
							onChange={(e) => setAngBaseDegS(Number(e.target.value))}
						/>
					</label>
				</div>
				<div className="grid grid-cols-3 gap-1">
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeLinearCount("x", +1))}
						onPointerUp={onRelease(() => changeLinearCount("x", -1))}
						onPointerCancel={() => changeLinearCount("x", -1)}
					>
						+X
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeLinearCount("y", +1))}
						onPointerUp={onRelease(() => changeLinearCount("y", -1))}
						onPointerCancel={() => changeLinearCount("y", -1)}
					>
						+Y
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeLinearCount("z", +1))}
						onPointerUp={onRelease(() => changeLinearCount("z", -1))}
						onPointerCancel={() => changeLinearCount("z", -1)}
					>
						+Z
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeLinearCount("x", -1))}
						onPointerUp={onRelease(() => changeLinearCount("x", +1))}
						onPointerCancel={() => changeLinearCount("x", +1)}
					>
						-X
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeLinearCount("y", -1))}
						onPointerUp={onRelease(() => changeLinearCount("y", +1))}
						onPointerCancel={() => changeLinearCount("y", +1)}
					>
						-Y
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeLinearCount("z", -1))}
						onPointerUp={onRelease(() => changeLinearCount("z", +1))}
						onPointerCancel={() => changeLinearCount("z", +1)}
					>
						-Z
					</button>
				</div>
				<div className="mt-2 grid grid-cols-3 gap-1">
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeAngularCount("x", +1))}
						onPointerUp={onRelease(() => changeAngularCount("x", -1))}
						onPointerCancel={() => changeAngularCount("x", -1)}
					>
						+Roll
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeAngularCount("y", +1))}
						onPointerUp={onRelease(() => changeAngularCount("y", -1))}
						onPointerCancel={() => changeAngularCount("y", -1)}
					>
						+Pitch
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeAngularCount("z", +1))}
						onPointerUp={onRelease(() => changeAngularCount("z", -1))}
						onPointerCancel={() => changeAngularCount("z", -1)}
					>
						+Yaw
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeAngularCount("x", -1))}
						onPointerUp={onRelease(() => changeAngularCount("x", +1))}
						onPointerCancel={() => changeAngularCount("x", +1)}
					>
						-Roll
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeAngularCount("y", -1))}
						onPointerUp={onRelease(() => changeAngularCount("y", +1))}
						onPointerCancel={() => changeAngularCount("y", +1)}
					>
						-Pitch
					</button>
					<button className="rounded bg-slate-800 px-2 py-1 hover:bg-slate-700"
						onPointerDown={onPress(() => changeAngularCount("z", -1))}
						onPointerUp={onRelease(() => changeAngularCount("z", +1))}
						onPointerCancel={() => changeAngularCount("z", +1)}
					>
						-Yaw
					</button>
				</div>
			</div>
			<div className="flex items-center justify-between">
				<button
					className="rounded bg-rose-600 px-3 py-2 text-white shadow hover:brightness-110 disabled:opacity-60"
					onClick={() => post("/control/stop")}
					disabled={busy}
				>
					STOP
				</button>
				<button
					className="rounded border border-slate-600 bg-slate-800 px-3 py-2 hover:bg-slate-700 disabled:opacity-60"
					onClick={async () => {
						// Pause jog to avoid fighting the absolute move
						if (jogEnabled) {
							await stopJog();
						}
						await post("/control/home");
					}}
					disabled={busy}
				>
					Home
				</button>
				<button
					className="rounded border border-slate-600 bg-slate-800 px-3 py-2 hover:bg-slate-700 disabled:opacity-60"
					onClick={async () => {
						if (jogEnabled) {
							await stopJog();
						}
						await post("/control/rest");
					}}
					disabled={busy}
				>
					Rest
				</button>
			</div>
		</div>
	);
}

export default ControlPanel;


