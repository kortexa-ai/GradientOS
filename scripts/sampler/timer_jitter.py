#!/usr/bin/env python3
"""
Best-effort timer jitter probe (ns/us) using clock_nanosleep(TIMER_ABSTIME).

This is NOT a replacement for cyclictest/rtla, but it's useful for:
- comparing an isolated RT CPU vs a non-isolated CPU
- checking whether background load is spilling onto isolated CPUs

Defaults:
- 1 kHz period (1000 us)
- 200 samples (~200 ms per invocation)
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import os
import sys
import time


class timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


_libc_path = ctypes.util.find_library("c") or "libc.so.6"
_libc = ctypes.CDLL(_libc_path, use_errno=True)
_clock_nanosleep = _libc.clock_nanosleep
_clock_nanosleep.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(timespec), ctypes.POINTER(timespec)]
_clock_nanosleep.restype = ctypes.c_int

_TIMER_ABSTIME = 1
_EINTR = 4


def _clock_nanosleep_abs(clock_id: int, target_ns: int) -> None:
    req = timespec(tv_sec=int(target_ns // 1_000_000_000), tv_nsec=int(target_ns % 1_000_000_000))
    rem = timespec()
    while True:
        rc = int(_clock_nanosleep(int(clock_id), _TIMER_ABSTIME, ctypes.byref(req), ctypes.byref(rem)))
        if rc == 0:
            return
        # EINTR: retry.
        if rc == _EINTR:
            continue
        # clock_nanosleep returns an error number (not errno).
        raise OSError(rc, f"clock_nanosleep failed (rc={rc})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Timer jitter probe (for Sampler)")
    ap.add_argument("--cpu", type=int, required=True, help="CPU to pin this probe to")
    ap.add_argument("--period-us", type=int, default=1000, help="Period in microseconds (default: 1000)")
    ap.add_argument("--samples", type=int, default=200, help="Number of wakeups to measure (default: 200)")
    ap.add_argument(
        "--fifo",
        action="store_true",
        help="Attempt to set SCHED_FIFO (requires root). Default is normal scheduling.",
    )
    ap.add_argument("--prio", type=int, default=80, help="SCHED_FIFO priority if --fifo (default: 80)")
    ap.add_argument(
        "--out",
        choices=("max_us", "max_ns"),
        default="max_us",
        help="Output format (default: max_us)",
    )
    args = ap.parse_args()

    cpu = int(args.cpu)
    period_ns = int(args.period_us) * 1000
    samples = max(1, int(args.samples))

    try:
        os.sched_setaffinity(0, {cpu})
    except Exception:
        # Ignore; still run.
        pass

    if args.fifo:
        try:
            os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(int(args.prio)))
        except PermissionError:
            # Don't fail the dashboard; just continue best-effort.
            pass
        except Exception:
            pass

    clock_id = time.CLOCK_MONOTONIC
    now = time.clock_gettime_ns(clock_id)
    target = now + period_ns

    max_jitter_ns = 0
    for _ in range(samples):
        _clock_nanosleep_abs(clock_id, target)
        woke = time.clock_gettime_ns(clock_id)
        jitter = woke - target
        if jitter < 0:
            jitter = -jitter
        if jitter > max_jitter_ns:
            max_jitter_ns = jitter
        target += period_ns

    if args.out == "max_ns":
        sys.stdout.write(str(int(max_jitter_ns)) + "\n")
    else:
        sys.stdout.write(f"{max_jitter_ns / 1000.0:.1f}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

