#!/bin/sh
set -eu

# Tune EtherCAT NIC for determinism (offloads/EEE).
# This must run BEFORE ethercat.service / RTCore.

IFACE="ethercat0"
if ! ip link show "${IFACE}" >/dev/null 2>&1; then
  # Pre-rename fallback (before reboot).
  if ip link show "eth0" >/dev/null 2>&1; then
    IFACE="eth0"
  fi
fi

ip link set "${IFACE}" up || true

# Disable common offloads that can add latency/jitter.
ethtool -K "${IFACE}" gro off gso off tso off lro off || true

# Disable Energy Efficient Ethernet (EEE).
ethtool --set-eee "${IFACE}" eee off || true

# Optional: only force speed/duplex if auto-negotiation proves unstable.
# ethtool -s "${IFACE}" speed 100 duplex full autoneg on || true

exit 0

