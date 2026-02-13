#!/bin/bash

set -euo pipefail

SERVICE_NAME="gradient-rt-motion.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"

echo "Uninstalling Gradient RT motion systemd service..."

echo "Stopping service..."
sudo systemctl stop "${SERVICE_NAME}" || true

echo "Disabling service..."
sudo systemctl disable "${SERVICE_NAME}" || true

echo "Removing service file..."
sudo rm -f "${SERVICE_PATH}"

echo "Removing RTCore binary..."
sudo rm -f /usr/local/bin/gradient-rt-motion || true

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Service uninstalled successfully!"

