#!/bin/bash

set -euo pipefail

SERVICE_NAME="gradient-rt-motion.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "Installing Gradient RT motion systemd service..."

echo "Building RTCore binary..."
make -C "${REPO_ROOT}/src/gradient_rt_motion" clean
make -C "${REPO_ROOT}/src/gradient_rt_motion"

echo "Installing RTCore binary to /usr/local/bin/gradient-rt-motion..."
sudo install -m 0755 "${REPO_ROOT}/src/gradient_rt_motion/gradient-rt-motion" /usr/local/bin/gradient-rt-motion

sudo cp "${SCRIPT_DIR}/${SERVICE_NAME}" "${SERVICE_PATH}"

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling service..."
sudo systemctl enable "${SERVICE_NAME}"

echo "Starting service..."
sudo systemctl start "${SERVICE_NAME}"

echo "Service status:"
sudo systemctl status "${SERVICE_NAME}" --no-pager

echo "Service installed successfully!"

