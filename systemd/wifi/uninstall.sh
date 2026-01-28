#!/bin/bash
set -euo pipefail

echo "Uninstalling Wi-Fi keepalive..."

sudo systemctl disable --now gradient-wifi-keepalive.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/gradient-wifi-keepalive.service
sudo rm -f /usr/local/sbin/gradient-wifi-keepalive.sh
sudo systemctl daemon-reload

echo "Done."

