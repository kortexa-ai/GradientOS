#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Wi-Fi keepalive (auto-reconnect)..."

sudo mkdir -p /etc/systemd/system /usr/local/sbin

sudo install -m 0755 "${SCRIPT_DIR}/gradient-wifi-keepalive.sh" /usr/local/sbin/gradient-wifi-keepalive.sh
sudo install -m 0644 "${SCRIPT_DIR}/gradient-wifi-keepalive.service" /etc/systemd/system/gradient-wifi-keepalive.service

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling + starting gradient-wifi-keepalive.service..."
sudo systemctl enable --now gradient-wifi-keepalive.service

echo "Done."

