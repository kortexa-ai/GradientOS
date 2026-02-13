#!/bin/bash

set -euo pipefail

SERVICE_NAME="gradient-rt-motion.service"

echo "Gradient RT motion service status:"
sudo systemctl status "${SERVICE_NAME}" --no-pager

echo ""
echo "Recent logs:"
sudo journalctl -u "${SERVICE_NAME}" -n 50 --no-pager

