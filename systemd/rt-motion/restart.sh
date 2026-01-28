#!/bin/bash

set -euo pipefail

SERVICE_NAME="gradient-rt-motion.service"

echo "Restarting Gradient RT motion service..."
sudo systemctl restart "${SERVICE_NAME}"

echo "Service status:"
sudo systemctl status "${SERVICE_NAME}" --no-pager

echo "Service restarted successfully!"

