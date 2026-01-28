#!/bin/sh
set -eu

# Pin EtherCAT NIC IRQs to CPU2-CPU3 (0xC on a 4-core CPU).
#
# NOTE:
# - This script is intentionally conservative and best-effort.
# - IRQ thread priority raising is left as a follow-up once IRQ names are verified on-host.

IFACE="ethercat0"
MASK_HEX="0xC"

if [ ! -f /proc/interrupts ]; then
  exit 0
fi

# Identify IRQ numbers for ethercat0 and pin them.
# We avoid grep/sed dependencies and use awk only.
for irq in $(awk -v iface="${IFACE}" '$0 ~ iface { gsub(/:/,"",$1); print $1 }' /proc/interrupts); do
  if [ -n "${irq}" ] && [ -d "/proc/irq/${irq}" ]; then
    echo "${MASK_HEX}" > "/proc/irq/${irq}/smp_affinity" || true
  fi
done

exit 0

