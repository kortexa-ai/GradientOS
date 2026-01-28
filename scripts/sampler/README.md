## Sampler dashboard for RTOS/EtherCAT bring-up

This folder contains a **Sampler** dashboard config and small helper scripts to live-monitor:
- **RTCore loop rate + jitter** (from `/run/gradient-rt-motion/metrics.json`)
- **Timer jitter** on an isolated RT CPU vs a non-RT CPU (user-space probe)
- **Per-core CPU usage**
- **RTCore thread placement** (CPU + RT priority) via `ps`

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
sudo apt-get install -y golang

go env -w GOPATH="$HOME/go"
go install github.com/sqshq/sampler@latest

sudo install -m 0755 "$HOME/go/bin/sampler" /usr/local/bin/sampler
sampler --help
```

---

### 3) Run the dashboard

```bash
sampler -c scripts/sampler/rtos_monitor.yml
```

Notes:
- The timer jitter probes are **best-effort user-space**. They’re useful for comparing
  *isolated RT CPUs vs non-isolated CPUs*, not for absolute certification-grade numbers.
- If you want to change which CPUs are compared, edit `scripts/sampler/rtos_monitor.yml`
  (defaults are CPU2 vs CPU0).

