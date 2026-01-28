#!/bin/bash
set -euo pipefail

# Restore the "appliance" assumption:
# - Drive is wired to the dedicated EtherCAT NIC (eth0 -> ethercat0)
# - IgH systemd unit binds via /etc/ethercat.conf (MAC c8:3e:a7:14:1c:75)
#
# Use after you've temporarily bound the master to a different NIC.

echo "Stopping any running EtherCAT master modules..."
sudo /usr/local/sbin/ethercatctl -c /etc/ethercat.conf stop || true

echo "Starting ethercat.service (uses /etc/ethercat.conf)..."
sudo systemctl start ethercat.service

echo ""
echo "Verify:"
echo "  sudo ethercat master"
echo "  sudo ethercat slaves -v"

