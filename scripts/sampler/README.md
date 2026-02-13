## Sampler dashboard for RTOS/EtherCAT bring-up

This is the canonical guide for the sampler dashboard under `scripts/sampler/`.

It monitors:
- RTCore loop rate + jitter (from `/run/gradient-rt-motion/metrics.json`)
- Timer jitter on isolated vs non-isolated CPUs (best-effort user-space probe)
- RTCore summary text

Sampler project: [`sqshq/sampler`](https://github.com/sqshq/sampler)

---

### 1) Prerequisites

Runbook context (kernel/EtherCAT/RTCore bring-up) is in `setup.md`.

For sampler itself you need:
- RTCore running and writing `/run/gradient-rt-motion/metrics.json`
- `sampler` installed and on `PATH`
- Python 3 available as `python3`

Start RTCore (installed binary example):

```bash
sudo /usr/local/bin/gradient-rt-motion --num-axes 2 --max-rpm 100
```

Quick metrics sanity check:

```bash
python3 ~/GradientOS/scripts/sampler/rtcore_metrics.py summary
```

---

### 2) Install Sampler (aarch64 note)

On this RevPi image, `sampler` is not installed by default.

Sampler upstream releases are commonly x86_64-only, so on aarch64 you usually build from source:

```bash
sudo apt-get update
sudo apt-get install -y golang libasound2-dev

go env -w GOPATH="$HOME/go"
# If you hit: "fatal error: alsa/asoundlib.h: No such file or directory"
# rerun with an explicit include path (some images need this for CGO):
CGO_CFLAGS='-I/usr/include' go install github.com/sqshq/sampler@latest

sudo install -m 0755 "$HOME/go/bin/sampler" /usr/local/bin/sampler
sampler --help
```

---

### 3) Run the dashboard (recommended)

Use the launcher script; it resolves repo paths, runs preflight checks, and exports the env vars used by the YAML config:

```bash
cd ~/GradientOS
./scripts/sampler/run_sampler.sh
```

Mode behavior:
- Local terminal: defaults to Sampler TUI.
- SSH terminal: defaults to text monitor (reliable).
- Force mode with `--tui` or `--text`.

You can also run it from another directory:

```bash
~/GradientOS/scripts/sampler/run_sampler.sh
```

---

### 4) Recommended sequence with `rtcore_jog` + monitoring

Use this when you want to move servos while watching monitoring in real time.

Terminal A (root): start RTCore

```bash
sudo /usr/local/bin/gradient-rt-motion --num-axes 2 --max-rpm 100
```

Terminal B (pi): start Sampler dashboard

```bash
cd ~/GradientOS
./scripts/sampler/run_sampler.sh
```

Terminal C (pi): run jog console and move axes

```bash
cd ~/GradientOS
python3 scripts/rtcore_jog.py console --rate-hz 2
```

Terminal D (optional): additional trend diagnostics

```bash
cd ~/GradientOS
python3 scripts/sampler/rtcore_diag_watch.py --interval 1.0 --duration 600
```

Important concurrency notes:
- Sampler and `rtcore_diag_watch.py` read `/run/gradient-rt-motion/metrics.json` and do not consume RTCore's IPC client slot.
- `rtcore_jog.py` is the IPC client; keep it as the only RTCore client session.
- Do not run the main controller and `rtcore_jog.py` at the same time.

---

### 5) Notes for integrated terminals (Cursor/VS Code)

- Best-effort support is provided.
- If the dashboard is blank, verify terminal size is at least 80x24.
- Some integrated terminals still fail with full-screen TUIs (`termbox` behavior).
- If it fails, use the fallback commands below or run from an external terminal/SSH session.

Quit Sampler with `q` (or `Ctrl+C`). If terminal state is garbled afterward, run `reset`.

---

### 6) SSH-specific troubleshooting

If it works locally on the RevPi but shows a blank screen over SSH, check this first:

- By default over SSH, launcher uses text mode:
  - `ssh -tt <host> "cd ~/GradientOS && ./scripts/sampler/run_sampler.sh"`
- To force the TUI over SSH:
  - `ssh -tt <host> "cd ~/GradientOS && ./scripts/sampler/run_sampler.sh --tui"`
- If the terminal type is problematic, try:

```bash
cd ~/GradientOS
GRADIENT_SAMPLER_TERM=xterm ./scripts/sampler/run_sampler.sh --tui
```

- If TUI is still blank, use fallback text monitoring below.

Known issue (tracked for later fix):
- On some SSH terminal/client combinations, Sampler full-screen TUI still renders blank even with `--tui`.
- Current workaround is to use `./scripts/sampler/run_sampler.sh` in default SSH text mode (or `--text` explicitly).
- TODO: investigate and fix SSH TUI compatibility (terminal capability / renderer behavior).

---

### 7) Quick fallback when TUI fails

Plain text polling:

```bash
watch -n 0.5 'python3 ~/GradientOS/scripts/sampler/rtcore_metrics.py summary'
```

One-shot values:

```bash
python3 ~/GradientOS/scripts/sampler/rtcore_metrics.py rt_hz
python3 ~/GradientOS/scripts/sampler/rtcore_metrics.py rt_max_jitter_us
python3 ~/GradientOS/scripts/sampler/rtcore_metrics.py summary
```

---

### 8) Delta diagnostics watcher (terminal-friendly)

For explicit trend detection (instead of charts):

```bash
cd ~/GradientOS
python3 scripts/sampler/rtcore_diag_watch.py --interval 1.0 --duration 600
```

This reports RT overruns, WKC mismatches, and EtherCAT lost-frame deltas with alert markers.

Tips:
- For a quick sanity check, use `--duration 30`.
- If EtherCAT polling is unavailable in your shell context, use `--no-ethercat`.
- Press `Ctrl+C` to stop early; a summary line is printed on exit.

---

### 9) CPU comparison defaults

The default dashboard compares CPU2 (isolated RT CPU) vs CPU0 in `scripts/sampler/rtos_monitor.yml`.

If your platform uses a different core layout, edit those CPU indices.

