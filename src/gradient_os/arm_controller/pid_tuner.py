# This script is used to tune the PID gains for the servos.
# IT DOES NOT WORK.
# and it takes a long time to run.
# so I'm not using it.

# TODO: fix it. the analysis could be better & higher resolution, tighter limits on values, etc.

import time
import math
import datetime
import csv
import numpy as np
from pathlib import Path
import os
import json

from . import utils
from . import servo_driver
from . import trajectory_execution


def _plot_tuning_heatmaps(results_csv_path: str, out_dir: Path):
    """Generate heatmaps/plots from grid_results.csv colored by overall score.

    Saves up to six figures:
      - heatmap_kp_ki.png, heatmap_kp_kd.png, heatmap_ki_kd.png (if 2D data exists)
      - phase_P.png (score vs Kp), phase_PI.png (score vs Ki), phase_PID.png (score vs Kd)
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import csv as _csv
        import math as _math
    except Exception as e:
        print(f"[PID Tune] WARNING: Matplotlib unavailable for heatmaps: {e}")
        return

    rows = []
    try:
        with open(results_csv_path, "r") as fp:
            reader = _csv.DictReader(fp)
            for r in reader:
                try:
                    rows.append({
                        "phase": r.get("phase") or "",
                        "kp": int(float(r["kp"])),
                        "ki": int(float(r["ki"])),
                        "kd": int(float(r["kd"])),
                        "score": float(r["score"]),
                    })
                except Exception:
                    continue
    except Exception as e:
        print(f"[PID Tune] WARNING: Failed to read results for plotting: {e}")
        return

    if not rows:
        return

    # Phase plots (1D)
    def _plot_phase(name: str, xs: list[int], scores: list[float], xlabel: str, outfile: str):
        if len(xs) <= 1:
            return
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        ax.plot(xs, scores, marker='o')
        ax.set_xlabel(xlabel)
        ax.set_ylabel('score (lower is better)')
        ax.set_title(name)
        fig.tight_layout()
        fig.savefig(out_dir / outfile)
        plt.close(fig)

    phaseP = [r for r in rows if r["phase"] == "P"]
    if phaseP:
        xs = [r["kp"] for r in phaseP]
        ys = [r["score"] for r in phaseP]
        _plot_phase("Phase P: score vs Kp", xs, ys, "Kp", "phase_P.png")

    phasePI = [r for r in rows if r["phase"] == "PI"]
    if phasePI:
        xs = [r["ki"] for r in phasePI]
        ys = [r["score"] for r in phasePI]
        _plot_phase("Phase PI: score vs Ki", xs, ys, "Ki", "phase_PI.png")

    phasePID = [r for r in rows if r["phase"] == "PID"]
    if phasePID:
        xs = [r["kd"] for r in phasePID]
        ys = [r["score"] for r in phasePID]
        _plot_phase("Phase PID: score vs Kd", xs, ys, "Kd", "phase_PID.png")

    # Heatmaps from whatever combinations exist: use min score over the third axis
    def _heatmap(param_x: str, param_y: str, other: str, filename: str):
        xs = sorted(set(r[param_x] for r in rows))
        ys = sorted(set(r[param_y] for r in rows))
        if len(xs) <= 1 or len(ys) <= 1:
            return
        index_x = {v: i for i, v in enumerate(xs)}
        index_y = {v: i for i, v in enumerate(ys)}
        grid = [[_math.nan for _ in xs] for __ in ys]
        # For each pair, take the min score over any value of the third parameter
        best_map = {}
        for r in rows:
            key = (r[param_x], r[param_y])
            s = r["score"]
            if key not in best_map or s < best_map[key]:
                best_map[key] = s
        for (xv, yv), s in best_map.items():
            grid[index_y[yv]][index_x[xv]] = s

        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        im = ax.imshow(grid, origin='lower', aspect='auto', cmap='viridis')
        ax.set_xticks(range(len(xs)))
        ax.set_yticks(range(len(ys)))
        ax.set_xticklabels(xs, rotation=45)
        ax.set_yticklabels(ys)
        ax.set_xlabel(param_x.upper())
        ax.set_ylabel(param_y.upper())
        ax.set_title(f"Score heatmap (min over {other.upper()})")
        fig.colorbar(im, ax=ax, label='score (lower is better)')
        fig.tight_layout()
        fig.savefig(out_dir / filename)
        plt.close(fig)

    _heatmap("kp", "ki", "kd", "heatmap_kp_ki.png")
    _heatmap("kp", "kd", "ki", "heatmap_kp_kd.png")
    _heatmap("ki", "kd", "kp", "heatmap_ki_kd.png")


def _generate_linear_joint_path(current_q: list[float], target_q: list[float], duration_s: float, frequency_hz: int) -> list[list[float]]:
    n_steps = max(2, int(duration_s * frequency_hz))
    path: list[list[float]] = []
    for k in range(n_steps):
        t = (k + 1) / n_steps
        q = [cq + t * (tq - cq) for cq, tq in zip(current_q, target_q)]
        # Clamp to limits
        for j in range(utils.NUM_LOGICAL_JOINTS):
            jmin, jmax = utils.LOGICAL_JOINT_LIMITS_RAD[j]
            if q[j] < jmin:
                q[j] = jmin
            elif q[j] > jmax:
                q[j] = jmax
        path.append(q)
    return path


def _generate_joint_only_sine_path(base_q: list[float], joint_index: int, amplitude_rad: float, frequency_hz: int, duration_s: float) -> list[list[float]]:
    n_steps = max(2, int(duration_s * frequency_hz))
    t_vals = np.linspace(0.0, 2.0 * math.pi, n_steps)
    path: list[list[float]] = []
    for t in t_vals:
        q = list(base_q)
        val = base_q[joint_index] + amplitude_rad * math.sin(t)
        jmin, jmax = utils.LOGICAL_JOINT_LIMITS_RAD[joint_index]
        q[joint_index] = max(jmin, min(jmax, val))
        path.append(q)
    return path


def _move_to_zero_pose(frequency_hz: int = 100, duration_s: float = 1.5):
    current_q = servo_driver.get_current_arm_state_rad(verbose=False)
    if not current_q:
        return
    target_q = [0.0] * utils.NUM_LOGICAL_JOINTS
    path = _generate_linear_joint_path(current_q, target_q, duration_s, frequency_hz)
    trajectory_execution._open_loop_executor_thread(path, frequency_hz, diagnostics=False, return_telemetry=False)


def tune_internal_pid_for_joint(
    logical_joint_index: int,
    kp_values: list[int] | None = None,
    ki_values: list[int] | None = None,
    kd_values: list[int] | None = None,
    amplitude_deg: float = 10.0,
    frequency_hz: int = 100,
    duration_s: float = 3.0,
    move_to_zero_first: bool = True,
    kp_step: int = 20,
    ki_step: int = 10,
    kd_step: int = 5,
) -> dict:
    """Grid-search tuner for internal servo PID per logical joint using open-loop.

    Generates a joint-only sine path, optionally moves to the zero pose first,
    runs open-loop while recording telemetry, scores error/smoothness, writes
    results, and applies the best gains to the physical servo(s) for that joint.
    """
    if kp_values is None:
        kp_values = list(range(max(1, kp_step), 201, max(1, kp_step)))
    if ki_values is None:
        ki_values = list(range(0, 101, max(1, ki_step)))
    if kd_values is None:
        kd_values = list(range(0, 51, max(1, kd_step)))

    amplitude_rad = math.radians(amplitude_deg)

    logical_to_servo_ids = {0: [10], 1: [20, 21], 2: [30, 31], 3: [40], 4: [50], 5: [60]}
    target_servo_ids = logical_to_servo_ids.get(logical_joint_index)
    if not target_servo_ids:
        print(f"[PID Tune] ERROR: Invalid logical joint index {logical_joint_index}")
        return {}

    base_q = servo_driver.get_current_arm_state_rad(verbose=False)
    if not base_q:
        print("[PID Tune] ERROR: Could not read current arm state.")
        return {}

    if move_to_zero_first:
        _move_to_zero_pose(frequency_hz=frequency_hz, duration_s=1.5)
        base_q = [0.0] * utils.NUM_LOGICAL_JOINTS

    test_path = _generate_joint_only_sine_path(base_q, logical_joint_index, amplitude_rad, frequency_hz, duration_s)

    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(f"diagnostics/tuning/internal_pid/{session_id}/joint_J{logical_joint_index+1}")
    out_dir.mkdir(parents=True, exist_ok=True)
    results_csv = out_dir / "grid_results.csv"

    def _score_trial(telemetry: dict) -> tuple[float, dict]:
        abs_err = telemetry.get("abs_errors_per_joint") or []
        actual = telemetry.get("actual_angles_per_joint") or []
        errs = abs_err[logical_joint_index] if logical_joint_index < len(abs_err) else []
        acts = actual[logical_joint_index] if logical_joint_index < len(actual) else []
        mean_abs_err = float(np.mean(errs)) if errs else 0.0
        rms_err = float(np.sqrt(np.mean(np.square(errs)))) if errs else 0.0
        vel_rms = 0.0
        acc_rms = 0.0
        jerk_rms = 0.0
        if len(acts) >= 2:
            v = np.diff(np.array(acts, dtype=float), n=1)
            vel_rms = float(np.sqrt(np.mean(v * v)))
        if len(acts) >= 3:
            a = np.diff(np.array(acts, dtype=float), n=2)
            acc_rms = float(np.sqrt(np.mean(a * a)))
        if len(acts) >= 4:
            j = np.diff(np.array(acts, dtype=float), n=3)
            jerk_rms = float(np.sqrt(np.mean(j * j)))
        smooth_cost = (0.7 * acc_rms) + (0.3 * jerk_rms)
        score = (rms_err + 0.5 * mean_abs_err) + 0.1 * smooth_cost
        return score, {
            "mean_abs_err_rad": mean_abs_err,
            "rms_err_rad": rms_err,
            "vel_rms_rad": vel_rms,
            "acc_rms_rad": acc_rms,
            "jerk_rms_rad": jerk_rms,
            "smooth_cost": smooth_cost,
        }

    best = {"score": float("inf"), "kp": 0, "ki": 0, "kd": 0}
    with open(results_csv, "w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["phase", "kp", "ki", "kd", "rms_err_rad", "mean_abs_err_rad", "vel_rms_rad", "acc_rms_rad", "jerk_rms_rad", "smooth_cost", "score"]) 
        # Full grid search over all combinations of Kp, Ki, and Kd
        for kp in kp_values:
            for ki in ki_values:
                for kd in kd_values:
                    print(f"[PID Tune] Sweep J{logical_joint_index+1}: Kp={kp}, Ki={ki}, Kd={kd}")
                    for sid in target_servo_ids:
                        servo_driver.set_servo_pid_gains(sid, kp, ki, kd)
                        time.sleep(0.02)
                    telemetry = trajectory_execution._open_loop_executor_thread(
                        test_path, frequency_hz, diagnostics=True, return_telemetry=True
                    )
                    if not telemetry:
                        print("[PID Tune] WARNING: No telemetry returned; skipping.")
                        continue
                    score, parts = _score_trial(telemetry)
                    writer.writerow([
                        "GRID",
                        kp,
                        ki,
                        kd,
                        parts["rms_err_rad"],
                        parts["mean_abs_err_rad"],
                        parts["vel_rms_rad"],
                        parts["acc_rms_rad"],
                        parts["jerk_rms_rad"],
                        parts["smooth_cost"],
                        score,
                    ])
                    fp.flush()
                    if score < best["score"]:
                        best.update({"score": score, "kp": kp, "ki": ki, "kd": kd})

    if best["kp"] is not None:
        for sid in target_servo_ids:
            servo_driver.set_servo_pid_gains(sid, int(best["kp"]), int(best["ki"]), int(best["kd"]))
            time.sleep(0.02)

        # Persist per-servo best gains to config/pid_gains.json for next boot
        try:
            cfg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config"))
            os.makedirs(cfg_dir, exist_ok=True)
            cfg_path = os.path.join(cfg_dir, "pid_gains.json")
            existing: dict[str, list[int]] = {}
            if os.path.isfile(cfg_path):
                with open(cfg_path, "r") as fp:
                    existing = json.load(fp)
            for sid in target_servo_ids:
                existing[str(sid)] = [int(best["kp"]), int(best["ki"]), int(best["kd"])]
            with open(cfg_path, "w") as fp:
                json.dump(existing, fp, indent=2)
            print(f"[PID Tune] Persisted best gains to {cfg_path}")
        except Exception as e:
            print(f"[PID Tune] WARNING: Failed to persist PID gains: {e}")

        print(f"[PID Tune] Best gains for J{logical_joint_index+1}: Kp={best['kp']}, Ki={best['ki']}, Kd={best['kd']}")
        print(f"[PID Tune] Results saved to {results_csv}")

        # Generate plots
        try:
            _plot_tuning_heatmaps(str(results_csv), out_dir)
            print(f"[PID Tune] Heatmaps saved to {out_dir}")
        except Exception as e:
            print(f"[PID Tune] WARNING: Failed to generate heatmaps: {e}")

    return {"joint": logical_joint_index, "best": {"kp": best["kp"], "ki": best["ki"], "kd": best["kd"]}, "results_csv": str(results_csv)}


