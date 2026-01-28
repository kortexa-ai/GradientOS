#!/bin/bash

set -euo pipefail

echo "Uninstalling EtherCAT host configuration templates..."

sudo systemctl disable --now gradient-ethercat-nic-tune.service || true
sudo systemctl disable --now gradient-irq-affinity.service || true
sudo systemctl disable --now gradient-cpu-performance.service || true

sudo rm -f /etc/systemd/network/10-ethercat0.link
sudo rm -f /etc/systemd/network/10-uplink0.link
sudo rm -f /etc/NetworkManager/conf.d/10-unmanaged-ethercat.conf
sudo rm -f /usr/local/sbin/gradient-ethercat-nic-tune.sh
sudo rm -f /usr/local/sbin/gradient-irq-affinity.sh
sudo rm -f /usr/local/sbin/gradient-cpu-performance.sh
sudo rm -f /etc/systemd/system/gradient-ethercat-nic-tune.service
sudo rm -f /etc/systemd/system/gradient-irq-affinity.service
sudo rm -f /etc/systemd/system/gradient-cpu-performance.service
sudo rm -f /etc/ethercat.conf

sudo systemctl daemon-reload

echo "Done."
echo "Note: if NIC names were changed, a reboot is required to revert."

