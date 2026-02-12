## RTCore jog tool (`scripts/rtcore_jog.py`)

This is a minimal bring-up CLI that talks **directly** to the RTCore daemon (`gradient-rt-motion`)
over its IPC socket (`/run/gradient-rt-motion/ipc.sock`).

Use it for:
- **Axis mapping** (which physical drive is `p0`, `p1`, …)
- **Single-axis motion tests** (enable/jog only the axis you want)
- **Encoder feedback visibility** (prints `0x6064` actual position counts + DS402 status)

Important: RTCore is **single-client** today. Don’t run the controller and `rtcore_jog.py` at the
same time.

---

### Prerequisites

- Drives wired in an EtherCAT chain, master connected to **CN3 (IN)** of the first drive.
- RTCore built:

```bash
make -C src/gradient_rt_motion
```

---

### Start RTCore (puts slaves into OP)

Run RTCore in one terminal (root):

```bash
sudo /usr/local/bin/gradient-rt-motion --num-axes 2 --max-rpm 100
```

If you have not installed to `/usr/local/bin` yet, use:

```bash
sudo ./src/gradient_rt_motion/gradient-rt-motion --num-axes 2 --max-rpm 100
```

Optional check (should show `OP` while RTCore is running):

```bash
sudo ethercat slaves
```

---

### Combined workflow: jog while monitoring

Use this terminal layout for bring-up sessions where you want live motion plus telemetry:

Terminal A (root): RTCore

```bash
sudo /usr/local/bin/gradient-rt-motion --num-axes 2 --max-rpm 100
```

Terminal B (pi): Sampler dashboard

```bash
cd ~/GradientOS
./scripts/sampler/run_sampler.sh
```

Note: over SSH this launcher defaults to text mode (recommended for reliability). Use `--tui` to force full-screen Sampler.

Terminal C (pi): jog console

```bash
cd ~/GradientOS
python3 scripts/rtcore_jog.py console --rate-hz 2
```

Terminal D (optional): long-run delta watcher

```bash
cd ~/GradientOS
python3 scripts/sampler/rtcore_diag_watch.py --interval 1.0 --duration 600
```

Concurrency rules:
- `rtcore_jog.py` uses the RTCore IPC socket and should be the only IPC client session.
- Sampler and `rtcore_diag_watch.py` read `/run/gradient-rt-motion/metrics.json`, so they can run alongside jog.
- Do not run the main controller and `rtcore_jog.py` at the same time.

If Sampler is blank in an integrated IDE terminal, switch that one terminal to:

```bash
watch -n 0.5 'python3 ~/GradientOS/scripts/sampler/rtcore_metrics.py summary'
```

---

### Recommended workflow: `console` (watch + commands in one session)

Because RTCore is single-client, use the interactive console:

```bash
python3 scripts/rtcore_jog.py console --rate-hz 2
# equivalent alias for validation runs:
python3 scripts/rtcore_jog.py test --rate-hz 2
```

Note: the console reads RTCore’s `STATUS_AXIS_CONFIG` message on connect, so it can interpret counts as q-units
without requiring you to pass `--counts-per-rev/--gear-ratio/--sign` flags.

By default, console watch lines now include diagnostics from
`/run/gradient-rt-motion/metrics.json` plus EtherCAT lost-frame polling:
- overrun counter + delta
- lost-frame counter + delta
- `rt_hz` and jitter (`last/max`, us)
- alert flags (`OVERRUN+N`, `WKC_MISMATCH`, `LOST+N`)

Disable diagnostics if you want minimal output:

```bash
python3 scripts/rtcore_jog.py console --rate-hz 2 --no-diag
```

#### Console commands

- **help**: show help
- **w**: toggle watch printing on/off
- **status**: print a full multi-line status block (per-axis)
- **config**: print RTCore axis scaling config (per-axis)
- **arm [0xMASK]**: arm RTCore and optionally set initial enable mask
- **disarm**: disarm RTCore (recommended before stopping RTCore)
- **enable 0xMASK**: overwrite the enable mask
- **disable 0xMASK**: clear bits from the enable mask
- **set AXIS Q**: set an **absolute** setpoint for one axis (q units; rotary is radians)
- **jog AXIS DELTA_Q**: jog **relative** by q units (uses current encoder position; rotary=rad, linear=m)
- **jogc AXIS DELTA_COUNTS**: jog **relative** by raw counts
- **reset [0xMASK]**: request a DS402 fault reset pulse (mask `0` means all axes)
- **quit**: exit the console

#### What you’re seeing (encoder + status)

Per axis (A6‑EC DS402 CSP mapping):
- **`pos_counts`**: encoder actual position (`0x6064`)
- **`sw`**: DS402 statusword (`0x6041`)
- **`ds402`**: RTCore-decoded DS402 state enum (see `ipc_v1.hpp`)
- **`err`**: error code (`0x603F`)
- **`mode_disp`**: mode display (`0x6061`) (8 means CSP)
- **`torque_raw`**: torque actual (`0x6077`)
- **`di`**: digital inputs (`0x60FD`)

Code reference (A6‑EC manual extracts):
- `docs/resources/a6ec_manual_codes.md` (human-readable)
- `docs/resources/a6ec_manual_codes.json` (machine-readable; generated from the PDF)

---

### Motion test (single axis / p0 only)

Inside the console:

```text
w
arm 0x1
jog 0 0.01
status
```

Notes:
- Start **tiny** (0.005–0.01 rad), increase slowly.
- `arm 0x1` enables **axis0 only** (EtherCAT `p0`).

---

### Multi-axis enable

Enable axis0 + axis1:

```text
arm 0x3
```

Jog axis1:

```text
jog 1 0.01
```

---

### Safe stop sequence

If you want to stop motion but keep the bus alive:

```text
disarm
```

If you want to fully stop RTCore:

1) In console:

```text
disarm
quit
```

2) Then stop RTCore (Ctrl+C in RTCore terminal).

RTCore includes a short shutdown grace window to push disable commands before exiting.

---

### Common errors / fixes

- **`RTCore socket not found: /run/gradient-rt-motion/ipc.sock`**
  - RTCore isn’t running, or it exited. Start RTCore first.

- **`Connection reset by peer` / `Broken pipe`**
  - RTCore rejected you because another client is connected (single-client policy).
  - Stop the controller or any other `rtcore_jog.py` session, or restart RTCore.

- **Drive display shows `ErC1.1` right after you stop RTCore**
  - Manual: **`ErC1.1` = Synchronization loss**.
  - This can happen when the EtherCAT master (SYNC/DC clock) disappears (bus drops from OP).
  - Checks:
    - Ensure RevPi is connected to drive **CN3 (IN)** and the chain is **CN4 (OUT) → next CN3 (IN)**.
    - Ensure the master’s sync/DC settings match the drive (RTCore uses DC/SYNC0; 1 kHz must be a multiple of 250 μs).
  - Practical note: if you want to stop motion but avoid a “bus-off” sync alarm, keep RTCore running and use `disarm`
    (servo disabled, bus still alive). If you fully stop RTCore, some drives will alarm until the bus returns.

- **Permission error**
  - The IPC socket is `0660 root:pi`. Run as user `pi` (normal shell), not as another user.

