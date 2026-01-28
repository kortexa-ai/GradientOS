#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing EtherCAT host configuration (NIC + tuning templates)..."
echo "NOTE: This modifies /etc and may require a reboot for NIC renaming."

sudo mkdir -p /etc/systemd/network /etc/NetworkManager/conf.d /etc/systemd/system /usr/local/sbin

echo "1) Installing deterministic NIC naming (.link)"
sudo install -m 0644 "${SCRIPT_DIR}/10-ethercat0.link" /etc/systemd/network/10-ethercat0.link
sudo install -m 0644 "${SCRIPT_DIR}/10-uplink0.link" /etc/systemd/network/10-uplink0.link

echo "2) Marking ethercat0 unmanaged (NetworkManager)"
sudo install -m 0644 "${SCRIPT_DIR}/10-unmanaged-ethercat.conf" /etc/NetworkManager/conf.d/10-unmanaged-ethercat.conf

echo "3) Installing NIC tune + IRQ affinity scripts"
sudo install -m 0755 "${SCRIPT_DIR}/gradient-ethercat-nic-tune.sh" /usr/local/sbin/gradient-ethercat-nic-tune.sh
sudo install -m 0755 "${SCRIPT_DIR}/gradient-irq-affinity.sh" /usr/local/sbin/gradient-irq-affinity.sh
sudo install -m 0755 "${SCRIPT_DIR}/gradient-cpu-performance.sh" /usr/local/sbin/gradient-cpu-performance.sh

echo "4) Installing systemd units for NIC tune + IRQ affinity + CPU governor"
sudo install -m 0644 "${SCRIPT_DIR}/gradient-ethercat-nic-tune.service" /etc/systemd/system/gradient-ethercat-nic-tune.service
sudo install -m 0644 "${SCRIPT_DIR}/gradient-irq-affinity.service" /etc/systemd/system/gradient-irq-affinity.service
sudo install -m 0644 "${SCRIPT_DIR}/gradient-cpu-performance.service" /etc/systemd/system/gradient-cpu-performance.service

echo "5) Installing /etc/ethercat.conf template (IgH master binds by MAC)"
sudo install -m 0644 "${SCRIPT_DIR}/ethercat.conf" /etc/ethercat.conf

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling NIC tune + IRQ affinity + CPU governor services..."
sudo systemctl enable gradient-ethercat-nic-tune.service
sudo systemctl enable gradient-irq-affinity.service
sudo systemctl enable gradient-cpu-performance.service

echo "Disabling irqbalance (if present)..."
sudo systemctl disable --now irqbalance.service 2>/dev/null || true

echo ""
echo "Done."
echo "Next steps:"
echo "  - (Optional but recommended) Apply RT CPU isolation params:"
echo "      sudo ${SCRIPT_DIR}/rtos-apply-cmdline.sh && reboot"
echo "  - Reboot to apply NIC renaming (eth0->uplink0, eth1->ethercat0)."
echo "  - Install IgH master (ethercat.service + libecrt + ethercat CLI)."

