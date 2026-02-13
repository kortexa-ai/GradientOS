#!/bin/bash

set -euo pipefail

SERVICE_NAME="gradient-rt-motion.service"

echo "Stopping Gradient RT motion service..."
sudo systemctl stop "${SERVICE_NAME}"

echo "Service stopped successfully!"

