## RTOS/EtherCAT plan overview + AI to‑do (read this first)

This folder contains:
- **`RTOS-ETHERCAT-plan.md`**: the full specification (RTOS tuning, IgH master, RTCore architecture, IPC, DS402, drive profiles, safety).
- **`Plan overview & to-do.md`** (this file): a short overview + an implementation action plan designed for an AI/engineer with fresh context.
- **`Uncertainties.md`**: a living checklist of everything we still need to validate on hardware.

Practical bring-up runbook (repo docs):
- `docs/ethercat/bringup.md`

### Locked decisions / invariants (do not change unless explicitly requested)
- **Host**: RevPi Connect 5 running Linux + **PREEMPT_RT** (appliance-style “freeze” after validation).
- **EtherCAT master**: **IgH** (`ec_master` + `libecrt`), with **DC/SYNC0** and 1 kHz target cycle.
- **RTCore language**: **C++17 user-space daemon** (`gradient-rt-motion`) linking `libecrt`.
- **EtherCAT wiring**: Cat6 minimum (100BASE‑TX), line topology, no switch/router.
- **NIC assignment**:
  - **`uplink0`** (front RJ45, currently `eth1`, has IP): `c8:3e:a7:14:1c:76`
  - **`ethercat0`** (front RJ45, currently `eth0`, EtherCAT): `c8:3e:a7:14:1c:75`
  - PiBridge NICs (not used for motion): `pileft` `c8:3e:a7:14:1c:77`, `piright` `c8:3e:a7:14:1c:78`

### What the implementer must produce (deliverables)
- **Host config**:
  - `/etc/systemd/network/10-ethercat0.link`, `/etc/systemd/network/10-uplink0.link`
  - `/etc/NetworkManager/conf.d/10-unmanaged-ethercat.conf`
  - `/etc/ethercat.conf` bound to `c8:3e:a7:14:1c:75`
  - systemd units/scripts for IRQ pinning + NIC tuning
- **RTCore**:
  - binary: `/usr/local/bin/gradient-rt-motion`
  - config: `/etc/gradient/ethercat.yaml`
  - systemd unit: `gradient-rt-motion.service` with RT scheduling + watchdog
- **GradientOS integration**:
  - Python backend: `src/gradient_os/arm_controller/backends/ethercat_rtcore/`
  - selection wiring via backend registry + controller startup flags/unit
- **Supportability**:
  - support bundle dumps (versions/topology/PDO/DC/jitter) and bounded logging

### Current implementation status (in repo)

The repo already contains an initial implementation scaffold:
- **RTCore daemon**: `src/gradient_rt_motion/` (IPC + optional `libecrt` loop)
- **Python backend proxy**: `src/gradient_os/arm_controller/backends/ethercat_rtcore/`
- **Host templates + systemd helpers**: `systemd/ethercat-host/` and `systemd/rt-motion/`
- **Diagnostics scripts**: `scripts/ethercat/diagnose_host.sh`
- **Pinned IgH installer**: `scripts/ethercat/install_igh.sh`

Recent progress (bring-up quality-of-life / monitoring):
- RTCore now supports **per-axis scaling** (`counts_per_rev/gear_ratio/sign/axis_type`) and publishes it over IPC (`MSG_STATUS_AXIS_CONFIG`).
- RTCore now implements **DS402 fault reset** (`CMD_FAULT_RESET`) as a short `0x0080` pulse sequence (still needs hardware validation).
- A6‑EC manual codes were extracted into:
  - `docs/resources/a6ec_manual_codes.md` (human)
  - `docs/resources/a6ec_manual_codes.json` (machine)
  and the jog tool now decodes `0x603F` to a readable “bus fault” name.
- RTCore writes `/run/gradient-rt-motion/metrics.json` (RT loop Hz/jitter/WKC/etc.) so dashboards can monitor without consuming the single-client IPC slot.
- A Sampler dashboard config exists at `scripts/sampler/rtos_monitor.yml` (requires installing `sampler`, typically built from source on aarch64).

Bring-up should proceed by validating hardware + master discovery first, then moving to RTCore cyclic motion.

---

## Fresh-context action plan (for an AI implementing this from scratch)

**Goal:** a step-by-step implementation checklist that assumes the implementer has *no prior chat context* and only has this repo + this document.

### 1.0 What is already specified vs what remains open

Already specified in `RTOS-ETHERCAT-plan.md`:
- **RTOS + NIC + IgH bring-up runbook** (section **14**) including MAC assignments.
- **RTCore language choice + integration boundary** (section **15**).
- **IPC protocol, structs, and semantics** (section **15.4**).
- **Non-DS402 tool/cabinet I/O model** (section **15.12**).
- **A6‑EC drive profile** (PDO layouts + DS402 sequencing + WKC math) (section **16**).

Still open (must be decided during implementation/bring-up):
- Exact EtherCAT tool I/O module(s) you will use (vendor ESI + PDO entries for `io_devices[].pdo.*`).
- Final DS402 stop option object values (`0x605A/0x605C/0x605E`) + 6085h ramp values validated on hardware.
- External axis mechanical conversion constants (rails lead, gearing, limits) for E1–E3.
- How/when the non‑RT controller (Python) will command external axes (as part of the motion plan vs manual control).
- Whether additional non-drive EtherCAT devices (I/O, safety) are included in the cyclic domain (affects expected WKC; see 16.6).

### 1.0.1 “Later when needed” backlog (not required for Phase A–F bring-up)
- **Tool/cabinet EtherCAT I/O module selection**
  - Pick the exact I/O hardware (vendor/model), commit ESI XML, and fill `io_devices[].pdo.*` indices/subindices.
- **Stop-mode validation + tuning**
  - Choose and validate: `0x605A/0x605C/0x605E` stop behaviors + `0x6085` ramp values on the real arm.
- **External axes (7th–9th) commissioning**
  - Define `lead_m_per_rev`, gearing, limits, homing/reference strategy for rails/positioners (E1–E3).
  - Decide whether external axes are integrated into planning (later) or remain manual axes initially.
- **Cabinet-level safety finalization**
  - E‑stop loop, STO wiring (if used), contactor strategy, brake master cut, and validation tests.
- **Production “freeze” artifacts**
  - final support-bundle evidence, version pinning, and recovery policy (bounded retries + latched faults).

### 1.1 Implementation phases (do in order; do not skip bring-up gates)

#### Phase A — Host/OS prerequisites (PREEMPT_RT appliance)
- [ ] Follow section **14.1**:
  - install RT kernel
  - apply CPU isolation parameters (CPU2–CPU3 RT, CPU0–CPU1 housekeeping)
  - disable `irqbalance`, set governor to performance
  - implement IRQ pinning service for EtherCAT NIC
  - run latency tests and record results

Deliverables:
- documented kernel version + cmdline + tuning scripts in support bundle

#### Phase B — NIC naming + EtherCAT port hardening
- [ ] Create the `systemd.link` rules from **14.2.1** with the real MACs.
- [ ] Configure NetworkManager unmanaged `ethercat0` from **14.2.2**.
- [ ] Install the NIC tuning service from **14.2.3** (offloads/EEE off).

Bring-up gate:
- `uplink0` keeps IP networking; `ethercat0` has **no IP** and stays UP.

#### Phase C — IgH master install + validation (no motion)
- [ ] Install/build IgH pinned version (14.3.1).
  - Important: do this **after** you are booted into the PREEMPT_RT kernel; IgH includes kernel modules and must match the running kernel/headers.
- [ ] Set `/etc/ethercat.conf` to bind master to MAC `c8:3e:a7:14:1c:75` (14.3.2).
- [ ] Validate topology and PDOs (14.4):
  - `ethercat slaves -v` shows expected chain
  - `ethercat pdos` matches planned `0x1702/0x1B02`
  - `ethercat dc` shows DC-capable slaves

Bring-up gate:
- You can reliably reach OP and see stable `ethercat slaves` output.

#### Phase D — RTCore skeleton (C++17) + service scaffolding
- [ ] Create RTCore code tree (see 14.5.1 / 15.9):
  - `src/gradient_rt_motion/` (recommended) or `src/gradient_rt/`
  - CMake build producing `/usr/local/bin/gradient-rt-motion`
- [ ] Implement RTCore runtime scaffolding (14.5.3):
  - RT thread (SCHED_FIFO, CPU2–CPU3, mlockall)
  - helper thread (CPU0–CPU1)
  - ring-buffer logging + stats
- [ ] Install `gradient-rt-motion.service` (14.7) and ensure ordering:
  - `Requires=ethercat.service`

Bring-up gate:
- RTCore starts and stays running under systemd, even if it does “no-op” motion.

#### Phase E — IPC implementation (Python ↔ RTCore)
- [ ] Implement the IPC protocol from **15.4**:
  - UDS handshake (`HELLO`/`WELCOME`) with SCM_RIGHTS fds
  - shared memory headers + rings + eventfd wakeups
  - status publisher: `STATUS_HELLO`, `STATUS_SNAPSHOT`, `STATUS_IO_SNAPSHOT` (even if empty initially)
- [ ] Add “topology hash” computation and enforcement (15.4 + 16.1).

Bring-up gate:
- Python can connect, read status snapshots, and RTCore rejects version mismatches.

#### Phase F — EtherCAT cyclic loop + domain mapping
- [ ] Implement `libecrt` domain mapping for A6‑EC profile (16.3–16.5):
  - register PDO entries per drive
  - set `0x6060=8` (CSP), write `0x607A`, drive `0x6040`
  - read `0x6041`, `0x6064`, `0x603F`, `0x60FD`
- [ ] Implement expected WKC logic (16.6) and treat mismatch as fault.
- [ ] Implement DC/SYNC0 setup and health policy (13.4 / 14.6).

Bring-up gate:
- cyclic loop runs at 1 kHz with stable WKC and bounded jitter; RTCore can hold position (no motion).

#### Phase G — DS402 state machine + stop/brake policy
- [ ] Implement DS402 decode + controlword sequencing (16.7–16.8).
- [ ] Implement brake gating policy (C05.10/C05.13) for gravity axes (sections 1 + 4.5 + 13.5).
- [ ] Implement safe stop ladder (13.7.6) and watchdogs (13.1.7 / 4.6).

Bring-up gate:
- enable/disable/fault-reset works deterministically; STOP triggers safe behavior.

#### Phase H — Python integration (`ethercat_rtcore` backend)
- [ ] Add a new backend package:
  - `src/gradient_os/arm_controller/backends/ethercat_rtcore/`
- [ ] Implement the `ActuatorBackend` methods per **15.11** (proxy behavior).
- [ ] Register backend name in `backends/registry.py` and update selection paths.
- [ ] **Critical migration fix:** gate Feetech legacy init in `run_controller.py` so selecting `ethercat_rtcore` does not call serial servo initialization.

Bring-up gate:
- Existing command handlers can move the arm through the backend without talking to serial servos.

#### Phase I — Tool/end-effector I/O (non-DS402)
- [ ] Choose EtherCAT I/O hardware and commit its ESI under `docs/resources/ethercat/esi/...`.
- [ ] Implement I/O PDO mapping in RTCore based on `io_devices[]` config (15.12).
- [ ] Implement `CMD_IO_WRITE` handling + `STATUS_IO_SNAPSHOT`.
- [ ] Map high-level tool commands in Python/API to `CMD_IO_WRITE` (e.g. gripper open/close).

Bring-up gate:
- tool outputs latch correctly and return to safe state on disarm.

#### Phase J — External axes (7th–9th) + multi-axis support
- [ ] Add E1–E3 as additional RTCore axes in `/etc/gradient/ethercat.yaml`.
- [ ] Define their `axis_type`, scaling (`lead_m_per_rev` for prismatic), and limits.
- [ ] Decide how Python will command them:
  - as part of the “arm” setpoints (extended planning), or
  - as separate manual commands first.

Bring-up gate:
- adding axes only requires config changes (no protocol rewrite).

#### Phase K — Freeze criteria and production hardening
- [ ] Run the acceptance tests (13.9) and archive support bundle.
- [ ] Freeze versions (10) + disable unattended upgrades.
- [ ] Define production recovery behavior (13.3.7) and enforce it in RTCore.

### 1.2 “Definition of done” (v1 industrial milestone)
- [ ] RevPi boots, configures RTOS, binds EtherCAT master, starts RTCore automatically.
- [ ] Topology is validated; mismatch refuses to arm.
- [ ] 1 kHz cyclic loop stable: no sustained overruns, WKC stable, DC stable.
- [ ] DS402 enable/disable/quick-stop and brake gating behave safely on faults.
- [ ] Python controller + API can command motion without any serial servo dependencies.
- [ ] Tool I/O (if present) is controlled via `CMD_IO_WRITE` and returns to safe state on disarm.