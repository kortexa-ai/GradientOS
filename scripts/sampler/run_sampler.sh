#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

config_path="${repo_root}/scripts/sampler/rtos_monitor.yml"
metrics_path="${GRADIENT_RTCORE_METRICS:-/run/gradient-rt-motion/metrics.json}"
python_bin="${GRADIENT_SAMPLER_PYTHON:-python3}"
term_value="${GRADIENT_SAMPLER_TERM:-${TERM:-xterm-256color}}"
mode="${GRADIENT_SAMPLER_MODE:-auto}" # auto|tui|text
text_interval="${GRADIENT_SAMPLER_TEXT_INTERVAL:-0.5}"

warn() {
  printf 'warn: %s\n' "$*" >&2
}

info() {
  printf '%s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: ./scripts/sampler/run_sampler.sh [--tui|--text]

Modes:
  --tui   Force Sampler TUI dashboard.
  --text  Force text monitoring loop (SSH-friendly).

Env overrides:
  GRADIENT_SAMPLER_MODE=auto|tui|text
  GRADIENT_SAMPLER_TEXT_INTERVAL=0.5
  GRADIENT_SAMPLER_TERM=xterm-256color
EOF
}

while (($#)); do
  case "$1" in
    --tui)
      mode="tui"
      ;;
    --text)
      mode="text"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      warn "Unknown argument: $1"
      usage
      exit 2
      ;;
  esac
  shift
done

is_ssh=0
if [[ -n "${SSH_CONNECTION:-}" || -n "${SSH_TTY:-}" ]]; then
  is_ssh=1
fi

if [[ "${mode}" == "auto" ]]; then
  if [[ "${is_ssh}" -eq 1 ]]; then
    mode="text"
    warn "SSH terminal detected: defaulting to text mode (use --tui to force TUI)."
  else
    mode="tui"
  fi
fi

if [[ ! -f "${config_path}" ]]; then
  warn "Sampler config not found: ${config_path}"
  exit 1
fi

missing_dep=0
if [[ "${mode}" == "tui" ]] && ! command -v sampler >/dev/null 2>&1; then
  warn "'sampler' not found on PATH."
  missing_dep=1
fi
if ! command -v "${python_bin}" >/dev/null 2>&1; then
  warn "Python binary not found: ${python_bin}"
  missing_dep=1
fi

if [[ "${missing_dep}" -ne 0 ]]; then
  info "Install/build dependencies first (see scripts/sampler/README.md)."
  exit 1
fi

if [[ ! -r "${metrics_path}" ]]; then
  warn "RTCore metrics file is not readable yet: ${metrics_path}"
  warn "Start RTCore first, then retry."
fi

if [[ "${mode}" == "text" ]]; then
  info "Launching text monitor (interval=${text_interval}s). Press Ctrl+C to stop."
  cd "${repo_root}"
  while true; do
    if [[ -t 1 ]] && command -v clear >/dev/null 2>&1; then
      clear
    fi
    "${python_bin}" "${repo_root}/scripts/sampler/rtcore_metrics.py" summary
    sleep "${text_interval}"
  done
fi

if [[ ! -t 0 || ! -t 1 ]]; then
  warn "Sampler TUI requires an interactive TTY."
  if [[ "${is_ssh}" -eq 1 ]]; then
    warn "If launching through ssh command mode, force TTY allocation with: ssh -tt <host> \"cd ~/GradientOS && ./scripts/sampler/run_sampler.sh --tui\""
  fi
  info "Use text mode instead: ./scripts/sampler/run_sampler.sh --text"
  exit 1
fi

if command -v tput >/dev/null 2>&1; then
  cols="$(tput cols 2>/dev/null || true)"
  rows="$(tput lines 2>/dev/null || true)"
  if [[ -n "${cols}" && -n "${rows}" ]] && (( cols < 80 || rows < 24 )); then
    warn "Terminal is ${cols}x${rows}; recommended minimum is 80x24."
  fi
fi

if [[ "${TERM_PROGRAM:-}" == "vscode" || -n "${VSCODE_GIT_IPC_HANDLE:-}" || -n "${VSCODE_INJECTION:-}" ]]; then
  warn "Detected Cursor/VS Code integrated terminal (best-effort TUI support)."
  warn "If Sampler is blank, use fallback:"
  warn "./scripts/sampler/run_sampler.sh --text"
fi

if [[ -z "${term_value}" || "${term_value}" == "dumb" || "${term_value}" == "unknown" ]]; then
  warn "TERM='${term_value:-unset}' is not suitable for full-screen TUI; falling back to xterm-256color."
  term_value="xterm-256color"
fi

if [[ "${is_ssh}" -eq 1 ]]; then
  warn "SSH terminal detected (TERM=${TERM:-unset}, launch TERM=${term_value})."
  warn "If screen stays blank, retry with: GRADIENT_SAMPLER_TERM=xterm ./scripts/sampler/run_sampler.sh"
fi

export GRADIENT_SAMPLER_REPO_ROOT="${repo_root}"
export GRADIENT_SAMPLER_PYTHON="${python_bin}"
export TERM="${term_value}"

info "Launching Sampler with config: ${config_path}"
info "Quit with q (or Ctrl+C). If terminal state is garbled, run: reset"
cd "${repo_root}"
exec sampler -c "${config_path}"
