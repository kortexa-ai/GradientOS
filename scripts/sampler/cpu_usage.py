#!/usr/bin/env python3
"""
Per-CPU usage (%) using /proc/stat deltas.

Designed for Sampler dashboards.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any


def _read_cpu_line(cpu: int) -> tuple[int, int] | None:
    """
    Returns (total_jiffies, idle_jiffies) for cpuN, or None if not found.
    """
    key = f"cpu{cpu}"
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith(key + " "):
                    continue
                parts = line.split()
                # cpu user nice system idle iowait irq softirq steal guest guest_nice
                vals = [int(x) for x in parts[1:]]
                if len(vals) < 4:
                    return None
                idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                total = sum(vals)
                return total, idle
    except Exception:
        return None
    return None


def _load_state(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_state(path: str, data: dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-CPU usage percent (for Sampler)")
    ap.add_argument("--cpu", type=int, required=True)
    ap.add_argument(
        "--state-dir",
        default=(
            os.environ.get("GRADIENT_SAMPLER_STATE_DIR")
            or os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "gradient-sampler")
        ),
        help="Directory for persistent delta state",
    )
    args = ap.parse_args()

    cpu = int(args.cpu)
    state_path = os.path.join(str(args.state_dir), f"cpu{cpu}.json")

    cur = _read_cpu_line(cpu)
    if cur is None:
        print("0")
        return 0

    total, idle = cur
    now_ns = time.monotonic_ns()

    prev = _load_state(state_path)
    prev_total = int(prev.get("total", 0) or 0)
    prev_idle = int(prev.get("idle", 0) or 0)

    # Save new state first (best-effort) so even if this sample is used, next call works.
    _save_state(state_path, {"time_ns": now_ns, "total": total, "idle": idle})

    dt_total = total - prev_total
    dt_idle = idle - prev_idle
    if dt_total <= 0:
        print("0")
        return 0

    usage = 100.0 * (float(dt_total - dt_idle) / float(dt_total))
    if usage < 0:
        usage = 0.0
    if usage > 100.0:
        usage = 100.0
    print(f"{usage:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

