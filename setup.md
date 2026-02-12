## GradientOS RTOS/EtherCAT/RTCore setup + self-test runbook (RevPi Connect 5)

This is a **copy/paste** checklist for bringing up and verifying:
**PREEMPT_RT kernel + CPU isolation + IgH EtherCAT master + `gradient-rt-motion` + monitoring**.

---

### Safety first (read)

- **Assume motors can move** once you enable/jog. Keep the mechanism safe/clear.
- Start with **tiny jogs** (e.g. `0.005–0.01 rad`) and increase slowly.
- RTCore has a **hard safety cap** when started with `--max-rpm 100` (recommended for bring-up).
- RTCore is **single-client** over IPC: don’t run the Python controller and `rtcore_jog.py` at the same time.

---

## A) One-time host setup (NIC rules + tuning + CPU isolation boot args)

From the repo root:

```bash
cd ~/GradientOS
```

### A1) Install EtherCAT host templates + tuning units

```bash
cd systemd/ethercat-host
./install.sh
```

What this does (high level):
- Installs NIC naming rules (`ethercat0`/`uplink0`) and marks `ethercat0` unmanaged.
- Installs + enables tuning units (NIC offload/EEE tuning, IRQ affinity pinning, CPU governor).
- Installs `/etc/ethercat.conf` template and a drop-in so `ethercat.service` uses it.

### A2) Apply RT CPU isolation boot args (recommended) + reboot

```bash
cd ~/GradientOS/systemd/ethercat-host
sudo ./rtos-apply-cmdline.sh
sudo reboot
```

---

## B) Self-test: prove you’re booted RT + isolation is applied

After reboot:

### B1) Confirm RT kernel (authoritative)

```bash
uname -a
grep -E '^CONFIG_PREEMPT_RT=' "/boot/config-$(uname -r)"
```

Expected:
- `uname -a` contains **`PREEMPT_RT`**
- `CONFIG_PREEMPT_RT=y`

Notes:
- On this RevPi kernel, `/sys/kernel/realtime` may **not exist** even when RT is enabled.

### B2) Confirm boot args + CPU isolation + IRQ default routing

```bash
cat /proc/cmdline
cat /sys/devices/system/cpu/isolated

# Default IRQ routing (hex mask). For 4 cores, "3" means CPU0-CPU1.
cat /proc/irq/default_smp_affinity
```

Expected:
- `/proc/cmdline` includes: `isolcpus=2,3 ... irqaffinity=0,1`
- `isolated` shows: `2-3` (or equivalent)
- `default_smp_affinity` is `3` (hex mask for CPUs 0–1)

Notes (important on this image):
- `/sys/devices/system/cpu/nohz_full` and `/sys/devices/system/cpu/rcu_nocbs` may be **missing** on this kernel build
  (because `CONFIG_NO_HZ_FULL` is not set). That’s not a failure signal.

### B3) Quick “one command” host sanity dump

```bash
cd ~/GradientOS
./scripts/ethercat/diagnose_host.sh
```

---

## C) Install IgH EtherCAT master (kernel modules + `ethercat` CLI) (one-time)

### C1) Make sure headers for the *running* kernel exist

```bash
uname -r
ls -l "/lib/modules/$(uname -r)/build"
```

### C2) Build + install pinned IgH (from repo script)

```bash
cd ~/GradientOS
./scripts/ethercat/install_igh.sh
```

### C3) Verify master is bound to the correct port (by MAC)

For this appliance wiring:
- **EtherCAT NIC MAC**: `c8:3e:a7:14:1c:75` (RevPi `eth0` / `ethercat0`)
- **Uplink MAC**: `c8:3e:a7:14:1c:76` (RevPi `eth1` / `uplink0`)

Check:

```bash
sudo cat /etc/ethercat.conf
```

Expected:
- `MASTER0_DEVICE="c8:3e:a7:14:1c:75"`
- `DEVICE_MODULES="generic"`

### C4) Enable/start EtherCAT service + confirm discovery

```bash
sudo systemctl enable --now ethercat.service

sudo ethercat master
sudo ethercat slaves -v
sudo ethercat slaves
```

Expected:
- `ethercat master`: Link **UP**, **Rx frames > 0**, **Lost frames ~0**
- `ethercat slaves`: at least your drives appear (usually **PREOP** until RTCore runs)

---

## D) Build + run RTCore (`gradient-rt-motion`)

### D1) Build + install the latest binary

```bash
cd ~/GradientOS
make -C src/gradient_rt_motion
sudo install -m 0755 src/gradient_rt_motion/gradient-rt-motion /usr/local/bin/gradient-rt-motion
```

### D2) Start RTCore manually (known-good for bring-up)

```bash
sudo /usr/local/bin/gradient-rt-motion --num-axes 2 --max-rpm 100
```

In another terminal, confirm bus health + OP:

```bash
sudo ethercat master
sudo ethercat slaves
```

Expected:
- `ethercat master`: `Active: yes`, Lost frames ~0
- `ethercat slaves`: both drives show **OP**

---

## E) Proof: RT scheduling + CPU pinning

In another terminal while RTCore is running:

```bash
pid=$(pgrep -n -f '[g]radient-rt-motion')
echo "pid=$pid"
ps -T -p "$pid" -o tid,cls,rtprio,pri,psr,comm
```

Expected:
- `rt-cycle` thread: `CLS` **FF** (FIFO), `RTPRIO` around **90**, `PSR` is **2 or 3**
- `metrics` thread: normal scheduling (`TS`), ideally on CPU0/1
- `ipc-helper` thread: appears when a client connects; should be CPU0/1

---

## F) Proof: RTCore metrics are live (monitoring input)

With RTCore running:

```bash
ls -l /run/gradient-rt-motion/
python3 -m json.tool /run/gradient-rt-motion/metrics.json | head -n 80
python3 scripts/sampler/rtcore_metrics.py summary
```

Expected (ballpark):
- `rt_hz` near **1000**
- `rt_overrun_count` **0**
- `wkc_actual == wkc_expected` (e.g. `6/6` for 2 axes in current mapping)

---

## G) Self-test: drive state + error codes via jog tool (single-client)

### G1) One-shot status

```bash
cd ~/GradientOS
python3 scripts/rtcore_jog.py status
```

### G2) Interactive console (recommended)

```bash
cd ~/GradientOS
python3 scripts/rtcore_jog.py console --rate-hz 2
# alias (same behavior, useful for validation runs):
python3 scripts/rtcore_jog.py test --rate-hz 2
```

Notes:
- Console watch output includes diagnostics by default (`ov` delta, WKC mismatch alerting, EtherCAT lost-frame deltas).
- Use `--no-diag` if you want the old minimal status output.

Inside the console:

```text
config
arm 0x1
jog 0 0.01
status
disarm
quit
```

Notes:
- `arm 0x1` enables **axis0 only** (safe single-axis bring-up).
- Use `reset` (or `fault_reset`) if you need to clear DS402 faults.

---

## H) Monitoring dashboard (Sampler)

RTCore already writes `/run/gradient-rt-motion/metrics.json`, so monitoring does **not** consume the single IPC client.

Sampler instructions are maintained in one place:
- `scripts/sampler/README.md` (canonical sampler guide)

Quick start:

```bash
cd ~/GradientOS
./scripts/sampler/run_sampler.sh
```

What to look for in the dashboard:
- **RTCore loop Hz** stays ~1000
- **RTCore wake jitter** stays bounded (watch max)
- **Timer jitter compare**: CPU2 (isolated RT CPU) should generally look better than CPU0
- If the dashboard is blank in an IDE terminal, use the fallback commands from `scripts/sampler/README.md`
  (or run from an external terminal/SSH session).

### H1) No Sampler? Quick "poor man's monitoring"

```bash
watch -n 0.5 'python3 ~/GradientOS/scripts/sampler/rtcore_metrics.py summary'
```

### H2) Delta diagnostics watcher (overrun/WKC/lost-frame trends)

This helper prints per-sample deltas and flags events that matter during soak:
- `OVERRUN+N` when `rt_overrun_count` increases
- `WKC_MISMATCH` when `wkc_actual != wkc_expected`
- `LOST+N` when EtherCAT `Lost frames` increases

Run for 10 minutes:

```bash
cd ~/GradientOS
python3 scripts/sampler/rtcore_diag_watch.py --interval 1.0 --duration 600
```

Quick 30-second check:

```bash
cd ~/GradientOS
python3 scripts/sampler/rtcore_diag_watch.py --interval 1.0 --duration 30
```

If `sudo ethercat master` is unavailable in your shell context, skip lost-frame polling:

```bash
cd ~/GradientOS
python3 scripts/sampler/rtcore_diag_watch.py --no-ethercat --interval 1.0 --duration 60
```

### H3) Combined terminal sequence (monitor + jog + diagnostics)

Use this exact order when you want to jog servos while watching telemetry:

1) Terminal A (root): keep RTCore running

```bash
sudo /usr/local/bin/gradient-rt-motion --num-axes 2 --max-rpm 100
```

2) Terminal B (pi): start Sampler (or fallback watch if TUI fails)

```bash
cd ~/GradientOS
./scripts/sampler/run_sampler.sh
```

Note: over SSH this launcher defaults to text monitoring; add `--tui` only if you want to force the full-screen dashboard.

3) Terminal C (pi): run jog console

```bash
cd ~/GradientOS
python3 scripts/rtcore_jog.py console --rate-hz 2
```

4) Terminal D (optional): run long soak diagnostics in parallel

```bash
cd ~/GradientOS
python3 scripts/sampler/rtcore_diag_watch.py --interval 1.0 --duration 600
```

Rules while running:
- `rtcore_jog.py` is the IPC client; keep only one jog/controller client connected.
- Sampler + `rtcore_diag_watch.py` read metrics and can run alongside jog.
- For safe stop: in console run `disarm`, then `quit`, then stop RTCore if needed.

---

## I) Optional: run RTCore as a systemd service (service mode)

### I1) Install the unit from the repo

```bash
cd ~/GradientOS/systemd/rt-motion
./install.sh
```

### I2) IMPORTANT: set correct args for your hardware (e.g. 2 axes)

By default RTCore’s compiled defaults assume **6 axes**. For your current 2-drive bring-up, edit:

```bash
sudo nano /etc/systemd/system/gradient-rt-motion.service
```

Change the `ExecStart` line to:

```text
ExecStart=/usr/local/bin/gradient-rt-motion --num-axes 2 --max-rpm 100
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gradient-rt-motion.service
sudo systemctl status gradient-rt-motion.service --no-pager
```

---

## Troubleshooting quick hits

- **`ethercat master` shows Rx=0 / Slaves=0**:
  - Wrong NIC bound (check `Main:` MAC), wrong cable/port, or not connected to drive CN3 (IN).
- **`Active: no` in `ethercat master`**:
  - Normal unless a `libecrt` app (RTCore) has activated the master.
- **`python3 scripts/rtcore_jog.py ...` says single-client / broken pipe**:
  - Another client is connected. Stop other controller/jog session or restart RTCore.
- **`nohz_full`/`rcu_nocbs` sysfs files missing**:
  - Expected on this kernel build; rely on `isolcpus` + IRQ affinity + measured results instead.

