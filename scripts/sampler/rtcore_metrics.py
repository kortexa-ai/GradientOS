#!/usr/bin/env python3
"""
Tiny helper that reads RTCore metrics from:
  /run/gradient-rt-motion/metrics.json

Designed for Sampler dashboards (numeric outputs for charts/gauges).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def _load_metrics(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _fnum(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _inum(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


def _get_axis(m: dict[str, Any], axis: int) -> dict[str, Any]:
    axes = m.get("axes", [])
    if isinstance(axes, list) and 0 <= axis < len(axes):
        ent = axes[axis]
        if isinstance(ent, dict):
            return ent
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Read RTCore metrics (for Sampler)")
    ap.add_argument(
        "--path",
        default=os.environ.get("GRADIENT_RTCORE_METRICS", "/run/gradient-rt-motion/metrics.json"),
        help="Path to RTCore metrics.json",
    )
    ap.add_argument(
        "--axis",
        type=int,
        default=0,
        help="Axis index for axis_* metrics (default: 0)",
    )
    ap.add_argument(
        "metric",
        help=(
            "Metric name. Examples: rt_hz, rt_cycles, rt_last_jitter_us, rt_max_jitter_us, "
            "wkc_actual, wkc_expected, wkc_ratio, master_state, armed, axis0_error_code, summary"
        ),
    )
    args = ap.parse_args()

    m = _load_metrics(str(args.path))
    metric = str(args.metric).strip()
    axis = int(args.axis)

    if metric == "rt_hz":
        print(f"{_fnum(m.get('rt_hz'), 0.0):.1f}")
        return 0

    if metric == "rt_cycles":
        print(_inum(m.get("rt_cycle_counter"), 0))
        return 0

    if metric == "rt_last_jitter_ns":
        print(_inum(m.get("rt_last_jitter_ns"), 0))
        return 0

    if metric == "rt_max_abs_jitter_ns":
        print(_inum(m.get("rt_max_abs_jitter_ns"), 0))
        return 0

    if metric == "rt_last_jitter_us":
        v = abs(_inum(m.get("rt_last_jitter_ns"), 0))
        print(f"{v / 1000.0:.1f}")
        return 0

    if metric == "rt_max_jitter_us":
        v = _inum(m.get("rt_max_abs_jitter_ns"), 0)
        print(f"{v / 1000.0:.1f}")
        return 0

    if metric == "wkc_actual":
        print(_inum(m.get("wkc_actual"), 0))
        return 0

    if metric == "wkc_expected":
        print(_inum(m.get("wkc_expected"), 0))
        return 0

    if metric == "wkc_ratio":
        a = _fnum(m.get("wkc_actual"), 0.0)
        e = _fnum(m.get("wkc_expected"), 0.0)
        if e <= 0:
            print("0")
            return 0
        print(f"{a / e:.3f}")
        return 0

    if metric == "master_state":
        print(_inum(m.get("master_state"), 0))
        return 0

    if metric == "armed":
        print(1 if _inum(m.get("armed"), 0) else 0)
        return 0

    if metric == "axis_error_code":
        a = _get_axis(m, axis)
        print(_inum(a.get("error_code"), 0))
        return 0

    if metric == "axis_statusword":
        a = _get_axis(m, axis)
        print(_inum(a.get("statusword"), 0))
        return 0

    if metric == "summary":
        # Multi-line, human-readable for Sampler textbox.
        num_axes = _inum(m.get("num_axes"), 0)
        cycle_ns = _inum(m.get("cycle_ns"), 0)
        print(f"RTCore metrics ({args.path})")
        print(f"  cycle_ns={cycle_ns} num_axes={num_axes}")
        print(f"  rt_hz={_fnum(m.get('rt_hz'), 0.0):.1f} rt_cycles={_inum(m.get('rt_cycle_counter'), 0)}")
        print(
            f"  rt_jitter_us(last/max)={abs(_inum(m.get('rt_last_jitter_ns'), 0))/1000.0:.1f}/"
            f"{_inum(m.get('rt_max_abs_jitter_ns'), 0)/1000.0:.1f}"
        )
        print(
            f"  wkc={_inum(m.get('wkc_actual'), 0)}/{_inum(m.get('wkc_expected'), 0)} "
            f"master_state={_inum(m.get('master_state'), 0)} armed={_inum(m.get('armed'), 0)} "
            f"enable_mask=0x{_inum(m.get('axis_enable_mask'), 0):x}"
        )
        axes = m.get("axes", [])
        if isinstance(axes, list):
            for i, ent in enumerate(axes[:num_axes]):
                if not isinstance(ent, dict):
                    continue
                err = _inum(ent.get("error_code"), 0)
                sw = _inum(ent.get("statusword"), 0)
                pos = _inum(ent.get("pos_counts"), 0)
                print(f"  axis{i}: err=0x{err:04x} sw=0x{sw:04x} pos_counts={pos}")
        return 0

    # Unknown metric: keep Sampler stable (numeric default).
    print("0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

