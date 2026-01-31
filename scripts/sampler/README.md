## Sampler dashboard for RTOS/EtherCAT bring-up

This folder contains a **Sampler** dashboard config and small helper scripts to live-monitor:
- **RTCore loop rate + jitter** (from `/run/gradient-rt-motion/metrics.json`)
- **Timer jitter** on an isolated RT CPU vs a non-RT CPU (user-space probe)
- (Optional) **Per-core CPU usage**
- (Optional) **RTCore thread placement** (CPU + RT priority) via `ps`

Sampler project: [`sqshq/sampler`](https://github.com/sqshq/sampler)

---

### 1) Make sure RTCore is running

RTCore writes a small metrics file here:
- `/run/gradient-rt-motion/metrics.json`

Start RTCore (example):

```bash
sudo ./src/gradient_rt_motion/gradient-rt-motion --num-axes 2 --max-rpm 100
```

---

### 2) Install Sampler (aarch64 note)

On this RevPi image, `sampler` is not installed by default.

Sampler upstream releases are commonly x86_64-only, so on **aarch64** you usually build from source:

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

### 3) Run the dashboard

```bash
TERM=xterm-256color sampler -c scripts/sampler/rtos_monitor.yml
```

Notes:
- If the dashboard is **blank**, your terminal is probably too small. This config is laid out for **80 cols x 24 rows**
  (try maximizing the terminal pane or reducing font size), then rerun.
- Quit Sampler with **`q`** (or `Ctrl+C`). If your terminal gets messed up afterward, run: `reset`
- If Sampler fails with a YAML parse error, it usually means a `sample:` command contains
  an unquoted `:` followed by a space (YAML treats `: ` specially). This repo’s config avoids
  that pattern; if you edit it, prefer `key=value` in echoed lines.
- The timer jitter probes are **best-effort user-space**. They’re useful for comparing
  *isolated RT CPUs vs non-isolated CPUs*, not for absolute certification-grade numbers.
- If you want to change which CPUs are compared, edit `scripts/sampler/rtos_monitor.yml`
  (defaults are CPU2 vs CPU0).

