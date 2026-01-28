#!/bin/bash

set -euo pipefail

# Apply RT CPU isolation parameters to the boot cmdline (RevPi/RPi style).
#
# Plan reference:
# - RTOS-ETHERCAT-PLAN/RTOS-ETHERCAT-plan.md §14.1.3
#
# Target CPU partitioning (4 cores):
# - housekeeping: CPU0-CPU1
# - RT cyclic + EtherCAT IRQs: CPU2-CPU3
#
# Parameters:
#   isolcpus=2,3 nohz_full=2,3 rcu_nocbs=2,3 irqaffinity=0,1
#
# This script is idempotent and keeps cmdline as a SINGLE LINE.

CMDLINE_PATH="/boot/firmware/cmdline.txt"
if [[ ! -f "${CMDLINE_PATH}" ]]; then
  echo "ERROR: ${CMDLINE_PATH} not found."
  exit 1
fi

required_params=(
  "isolcpus=2,3"
  "nohz_full=2,3"
  "rcu_nocbs=2,3"
  "irqaffinity=0,1"
)

current="$(tr -d '\n' < "${CMDLINE_PATH}")"

backup="${CMDLINE_PATH}.bak.$(date +%Y%m%d_%H%M%S)"
cp "${CMDLINE_PATH}" "${backup}"
echo "Backup: ${backup}"

updated="${current}"
for p in "${required_params[@]}"; do
  if [[ "${updated}" != *"${p}"* ]]; then
    updated="${updated} ${p}"
  fi
done

# Normalize whitespace.
updated="$(echo "${updated}" | tr -s ' ')"

echo -n "${updated}" > "${CMDLINE_PATH}"
echo "" >> "${CMDLINE_PATH}"

echo "Updated ${CMDLINE_PATH}:"
echo "${updated}"
echo ""
echo "Reboot required for changes to take effect."

