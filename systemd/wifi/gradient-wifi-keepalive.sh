#!/usr/bin/env bash
set -euo pipefail

# Simple Wi-Fi keepalive loop for RevPi/NetworkManager.
#
# Defaults can be overridden via environment variables or positional args:
#   IFACE="wlan0" CONNECTION_NAME="My WiFi" SLEEP_SECONDS=10 ./gradient-wifi-keepalive.sh
#
# This script is intended to be run as root (systemd service), because it:
# - forces the Wi-Fi interface admin-up when it is down
# - unblocks rfkill if WLAN is soft-blocked

IFACE="${1:-${IFACE:-wlan0}}"
CONNECTION_NAME="${2:-${CONNECTION_NAME:-Aussie Broadband 9745}}"
SLEEP_SECONDS="${3:-${SLEEP_SECONDS:-10}}"

_ts() { date -Is; }
_log() { echo "[$(_ts)] gradient-wifi-keepalive: $*"; }

_rfkill_unblock_wlan() {
  # rfkill sysfs: state=1 means unblocked/enabled.
  for d in /sys/class/rfkill/rfkill*; do
    [[ -f "${d}/type" ]] || continue
    local type
    type="$(<"${d}/type")"
    [[ "${type}" == "wlan" ]] || continue

    local state
    state="$(<"${d}/state")"
    if [[ "${state}" != "1" ]]; then
      echo 1 > "${d}/state" || true
      _log "rfkill: unblocked (${d})"
    fi
  done
}

_iface_is_admin_up() {
  local line
  line="$(ip link show "${IFACE}" 2>/dev/null | head -n 1 || true)"
  [[ -n "${line}" ]] || return 1
  [[ "${line}" == *",UP"* || "${line}" == *"UP,"* || "${line}" == *"<"*UP*">"* ]]
}

_ensure_iface_admin_up() {
  if ! _iface_is_admin_up; then
    _log "interface ${IFACE} is admin-down; forcing up"
    ip link set "${IFACE}" up || true
  fi
}

_nm_state_code() {
  # e.g. "100 (connected)" -> "100"
  local s
  s="$(nmcli -g GENERAL.STATE device show "${IFACE}" 2>/dev/null || true)"
  s="${s%% *}"
  echo "${s}"
}

_nm_ipv4_addr() {
  nmcli -g IP4.ADDRESS device show "${IFACE}" 2>/dev/null || true
}

_try_reconnect() {
  _log "attempting reconnect: ${CONNECTION_NAME} on ${IFACE}"
  timeout 25s nmcli radio wifi on >/dev/null 2>&1 || true
  timeout 25s nmcli dev wifi rescan ifname "${IFACE}" >/dev/null 2>&1 || true
  timeout 25s nmcli con up "${CONNECTION_NAME}" >/dev/null 2>&1 || true
}

fail_count=0

_log "starting (iface=${IFACE}, connection=${CONNECTION_NAME}, sleep=${SLEEP_SECONDS}s)"

while true; do
  _rfkill_unblock_wlan
  _ensure_iface_admin_up

  state="$(_nm_state_code)"
  ip4="$(_nm_ipv4_addr)"

  if [[ "${state}" == "100" && -n "${ip4}" ]]; then
    fail_count=0
    sleep "${SLEEP_SECONDS}"
    continue
  fi

  fail_count=$((fail_count + 1))
  _log "not connected (state=${state:-?}, ip4=${ip4:-none}, failures=${fail_count})"

  _try_reconnect

  # If we keep failing for ~1 minute, restart NetworkManager to un-stick the stack.
  if (( fail_count >= 6 )); then
    _log "too many failures; restarting NetworkManager"
    systemctl restart NetworkManager || true
    fail_count=0
    sleep 5
  fi

  sleep "${SLEEP_SECONDS}"
done

