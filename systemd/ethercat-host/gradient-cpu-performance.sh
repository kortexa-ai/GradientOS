#!/bin/sh
set -eu

# Best-effort set CPU governor to "performance" to reduce jitter.
# Safe to run on systems without cpufreq (it will no-op).

for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  if [ -f "${gov}" ]; then
    echo performance > "${gov}" 2>/dev/null || true
  fi
done

exit 0

