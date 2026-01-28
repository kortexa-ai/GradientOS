#!/bin/bash

set -euo pipefail

echo "=== GradientOS EtherCAT host diagnostics ==="
echo ""

echo "## Kernel"
uname -a || true
echo ""

echo "## CPU"
command -v lscpu >/dev/null 2>&1 && lscpu | sed -n '1,25p' || true
echo ""

echo "## Kernel cmdline"
cat /proc/cmdline || true
echo ""

echo "## Boot cmdline file(s)"
for p in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
  if [ -f "$p" ]; then
    echo "- $p:"
    cat "$p"
  fi
done
echo ""

echo "## NICs"
ip -brief link || true
echo ""

echo "## NetworkManager devices"
command -v nmcli >/dev/null 2>&1 && nmcli dev status || true
echo ""

echo "## EtherCAT prerequisites"
kver="$(uname -r)"
if [ -e "/lib/modules/$kver/build" ]; then
  echo "- kernel headers: present (/lib/modules/$kver/build)"
else
  echo "- kernel headers: MISSING (/lib/modules/$kver/build not found)"
fi

if command -v ethercat >/dev/null 2>&1; then
  echo "- ethercat CLI: present ($(command -v ethercat))"
else
  echo "- ethercat CLI: missing"
fi

if [ -f /etc/ethercat.conf ]; then
  echo "- /etc/ethercat.conf:"
  cat /etc/ethercat.conf
else
  echo "- /etc/ethercat.conf: missing"
fi

echo ""
echo "Done."

