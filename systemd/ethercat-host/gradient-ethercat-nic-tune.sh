#!/bin/sh
set -eu

# Tune EtherCAT NIC for determinism (offloads/EEE).
# This must run BEFORE ethercat.service / RTCore.

IFACE="ethercat0"

ip link set "${IFACE}" up || true

# Disable common offloads that can add latency/jitter.
ethtool -K "${IFACE}" gro off gso off tso off lro off || true

# Disable Energy Efficient Ethernet (EEE).
ethtool --set-eee "${IFACE}" eee off || true

# Optional: only force speed/duplex if auto-negotiation proves unstable.
# ethtool -s "${IFACE}" speed 100 duplex full autoneg on || true

exit 0

