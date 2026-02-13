#!/usr/bin/env python3
"""
Live RTCore/EtherCAT diagnostics watcher.

Prints per-sample deltas so regressions are obvious during bring-up/soak:
- rt_overrun_count delta
- WKC mismatch samples
- EtherCAT lost frame delta (from `ethercat master`)
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class Sample:
    overrun: int = 0
    wkc_actual: int = 0
    wkc_expected: int = 0
    rt_hz: float = 0.0
    rt_last_jitter_ns: int = 0
    rt_max_abs_jitter_ns: int = 0
    master_state: int = 0
    armed: int = 0
    lost_frames: int | None = None


def _inum(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _fnum(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_metrics(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _read_lost_frames(cmd: str) -> int | None:
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    m = re.search(r"^\s*Lost frames:\s*(\d+)\s*$", proc.stdout, flags=re.MULTILINE)
    if not m:
        return None
    return _inum(m.group(1), 0)


def _sample(metrics_path: str, lost_frames: int | None) -> Sample:
    m = _load_metrics(metrics_path)
    return Sample(
        overrun=_inum(m.get("rt_overrun_count"), 0),
        wkc_actual=_inum(m.get("wkc_actual"), 0),
        wkc_expected=_inum(m.get("wkc_expected"), 0),
        rt_hz=_fnum(m.get("rt_hz"), 0.0),
        rt_last_jitter_ns=_inum(m.get("rt_last_jitter_ns"), 0),
        rt_max_abs_jitter_ns=_inum(m.get("rt_max_abs_jitter_ns"), 0),
        master_state=_inum(m.get("master_state"), 0),
        armed=_inum(m.get("armed"), 0),
        lost_frames=lost_frames,
    )


def _fmt_delta(current: int, previous: int | None) -> str:
    if previous is None:
        return "(n/a)"
    delta = current - previous
    sign = "+" if delta >= 0 else ""
    return f"({sign}{delta})"


def main() -> int:
    ap = argparse.ArgumentParser(description="Watch RTCore + EtherCAT diagnostic deltas")
    ap.add_argument(
        "--metrics-path",
        default="/run/gradient-rt-motion/metrics.json",
        help="Path to RTCore metrics.json",
    )
    ap.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Sample interval in seconds (default: 1.0)",
    )
    ap.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Stop after this many seconds (default: 0 = run until Ctrl+C)",
    )
    ap.add_argument(
        "--ethercat-cmd",
        default="sudo ethercat master",
        help="Command used to read EtherCAT lost frames",
    )
    ap.add_argument(
        "--ethercat-every",
        type=int,
        default=1,
        help="Run --ethercat-cmd every N samples (default: 1)",
    )
    ap.add_argument(
        "--no-ethercat",
        action="store_true",
        help="Skip EtherCAT lost-frame polling",
    )
    args = ap.parse_args()

    if args.interval <= 0:
        print("interval must be > 0", file=sys.stderr)
        return 2
    if args.ethercat_every <= 0:
        print("ethercat-every must be > 0", file=sys.stderr)
        return 2

    print(
        "time | overrun (d) | wkc | lost_frames (d) | hz | jitter_us(last/max) | "
        "master_state armed | alerts"
    )

    start = time.monotonic()
    prev: Sample | None = None
    sample_count = 0
    mismatch_samples = 0
    overrun_growth_total = 0
    lost_growth_total = 0

    try:
        while True:
            lost_frames = None
            if not args.no_ethercat and (sample_count % args.ethercat_every == 0):
                lost_frames = _read_lost_frames(args.ethercat_cmd)
            elif prev is not None:
                lost_frames = prev.lost_frames

            cur = _sample(args.metrics_path, lost_frames)

            if cur.wkc_expected > 0 and cur.wkc_actual != cur.wkc_expected:
                mismatch_samples += 1

            d_overrun = 0 if prev is None else (cur.overrun - prev.overrun)
            if d_overrun > 0:
                overrun_growth_total += d_overrun

            d_lost = 0
            if prev is not None and cur.lost_frames is not None and prev.lost_frames is not None:
                d_lost = cur.lost_frames - prev.lost_frames
                if d_lost > 0:
                    lost_growth_total += d_lost

            alerts: list[str] = []
            if d_overrun > 0:
                alerts.append(f"OVERRUN+{d_overrun}")
            if cur.wkc_expected > 0 and cur.wkc_actual != cur.wkc_expected:
                alerts.append("WKC_MISMATCH")
            if d_lost > 0:
                alerts.append(f"LOST+{d_lost}")
            alert_text = ",".join(alerts) if alerts else "-"

            lost_text = "n/a"
            lost_delta = "(n/a)"
            if cur.lost_frames is not None:
                lost_text = str(cur.lost_frames)
                lost_delta = _fmt_delta(cur.lost_frames, None if prev is None else prev.lost_frames)

            print(
                f"{time.strftime('%H:%M:%S')} | "
                f"{cur.overrun} {_fmt_delta(cur.overrun, None if prev is None else prev.overrun)} | "
                f"{cur.wkc_actual}/{cur.wkc_expected} | "
                f"{lost_text} {lost_delta} | "
                f"{cur.rt_hz:.1f} | "
                f"{abs(cur.rt_last_jitter_ns) / 1000.0:.1f}/{cur.rt_max_abs_jitter_ns / 1000.0:.1f} | "
                f"{cur.master_state} {cur.armed} | "
                f"{alert_text}"
            )

            prev = cur
            sample_count += 1

            if args.duration > 0 and (time.monotonic() - start) >= args.duration:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass

    print(
        "summary: "
        f"samples={sample_count} "
        f"overrun_growth_total={overrun_growth_total} "
        f"wkc_mismatch_samples={mismatch_samples} "
        f"lost_frame_growth_total={lost_growth_total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
