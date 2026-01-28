## RTOS/EtherCAT uncertainties / open questions

Purpose: track anything we are **not 100% sure about yet**, so we can validate it
systematically during bring-up (and avoid “tribal knowledge” getting lost).

Update this file whenever:
- we make a new assumption, or
- a hardware test reveals a mismatch, or
- we find a “works on my setup” detail that should be pinned.

---

### Hardware / wiring / topology

- [ ] **Slave order / axis mapping**: which EtherCAT slave positions correspond to which physical joints on your test setup?
  - Python mapping is configurable: `GRADIENT_RTCORE_CONTROL_JOINTS="jA,jB,..."` (1-based joint numbers; length must match `num_axes`).
  - Tip: for a *p0-only motion test*, you can also restrict auto-arming to a subset of axes via `GRADIENT_RTCORE_AUTO_ARM_MASK=0x1` (axis0 only).
- [ ] **Drive identity tuple**: confirm VendorId/ProductCode/RevisionNo from `ethercat slaves -v` matches the expected A6‑EC tuple in the plan (or update the constants if your test drives differ).
  - Update (confirmed): `VendorId=0x00400000`, `ProductCode=0x00000715`, `RevisionNo=0x00002EF8` (device name `AS715N_sAxis_V0.10`).
  - Update (CoE objects): `0x1008="AS715N-DRIVER"`, `0x1009="V001"` (HW ver), `0x100A="V512"` (SW ver).
  - Note: `0x1018:03` (CoE identity revision) reported `0x00005612` on this unit, which differs from the SII revision `0x00002EF8` shown by `ethercat slaves -v`. Treat SII as authoritative for IgH identity matching.
- [ ] **Link / slave discovery on the dedicated EtherCAT NIC**: with the **appliance wiring** (RevPi `eth0` / `ethercat0` → drive CN3/IN), confirm:
  - `ethercat master` shows **Rx frames > 0** and **frame loss near 0**
  - `ethercat slaves -v` shows at least **1** slave
  - Manual (A6-EC ch3.8): EtherCAT ports are **CN3 (IN)** and **CN4 (OUT)**. Master should connect to **CN3 (IN)**.
  - Update (important): on this RevPi image/hardware, EtherCAT discovery was confirmed working when the master was bound to **`eth0`** (`macb`), but repeatedly failed (Tx only, Rx=0) on **`eth1`** (`lan743x`) despite Link=UP. We therefore treat `eth0` as the dedicated EtherCAT NIC for the appliance.
  - If you ever see Link=UP but Rx frames=0 and Slaves=0 again: first confirm the **`Main:` MAC in `ethercat master` matches the port plugged into the drive**, or stop/unload and restart the master with the correct `MASTER0_DEVICE`.

- [ ] **Two-drive chain present (bring-up)**: we now have **2 slaves** discovered (positions `0` and `1`).
  - Confirm which physical joints they correspond to (cables on drives).
  - Update (observed): test setup reports **`p0 → J5`** and **`p1 → J3`** (treat this as tentative until cables are labeled).
  - PDO selection note: drives can boot with default assignment `0x1701/0x1B01`; for RTCore bring-up we set `0x1C12:01=0x1702` and `0x1C13:01=0x1B02` per slave (must be re-applied after drive power-cycle).

---

### Host OS / NIC configuration

- [ ] **NIC renaming takes effect**: reboot required for `eth0/eth1 → ethercat0/uplink0` (`systemd.link` files).
- [ ] **NetworkManager unmanaged**: confirm `ethercat0` (and pre-rename `eth0`) stay unmanaged (no DHCP, no IP routes).
- [ ] **NIC tuning**: confirm offloads + EEE are actually disabled and stable on the EtherCAT port (`ethtool -k/-a/--show-eee`).
- [ ] **Negotiated speed/duplex**: confirm the bus runs at expected **100 Mbps full** (typical for many slaves).

---

### RT CPU partitioning / latency

- [ ] **Isolation parameters validated**: `isolcpus=2,3 nohz_full=2,3 rcu_nocbs=2,3 irqaffinity=0,1` were appended to `/boot/firmware/cmdline.txt` — requires reboot, then verify CPU2–CPU3 are truly isolated.
- [ ] **IRQ pinning correctness**: confirm the EtherCAT NIC IRQ names/lines in `/proc/interrupts` match the script’s assumptions and the mask `0xC` (CPU2–CPU3) is correct on this CPU topology.
- [ ] **Jitter acceptance**: run `cyclictest`/`rtla timerlat` under load and record actual jitter distributions (target thresholds are in the plan, but we need real numbers for this image).
  - Update (implemented): RTCore now measures **wakeup jitter** in the cyclic thread and publishes:
    - `StatusSnapshotV1.cycle_jitter_ns` (IPC)
    - `/run/gradient-rt-motion/metrics.json` (best-effort, no IPC client required)
  - Update (implemented): a Sampler dashboard config exists at `scripts/sampler/rtos_monitor.yml` to compare:
    - RTCore loop Hz + jitter
    - user-space timer jitter on an isolated CPU vs a non-isolated CPU
    - per-core CPU usage
  - Note: `cyclictest`/`rtla` were not installed by default on this image; the Sampler timer probe is *comparative* (useful for “RT vs non-RT”), but still collect “gold standard” numbers once the proper tools are installed.

---

### IgH (EtherLab) master installation & service model

- [ ] **Module load at boot**: confirm `ec_master` + `ec_generic` load reliably on this kernel and create the master device.
- [ ] **Config file location**: ensure the runtime uses `/etc/ethercat.conf` (not `/usr/local/etc/ethercat.conf`) and that `MASTER0_DEVICE=<ethercat MAC>` is correct.
- [ ] **Service ordering**: confirm `ethercat.service` starts *after* NIC rename/tuning units and *before* `gradient-rt-motion.service`.
- [ ] **Kernel headers “prepared enough”**: we installed RevPi headers and had to seed a missing `auto.conf.cmd` to satisfy IgH’s `configure` checks.
  - Validate that the resulting modules load cleanly after reboot (`modinfo`, `dmesg`, `lsmod`).
  - If anything is flaky, we may need a full matching kernel source tree instead of “headers only”.

---

### DS402 + A6‑EC commissioning unknowns (must be verified on real drives)

- [ ] **PDO sets & layouts**: confirm the drive is actually using RxPDO `0x1702` and TxPDO `0x1B02` (verify with `ethercat pdos`).
  - Manual (A6-EC ch8) says `0x1702` (Output) fixed mapping contains: `6040` control word, `607A` target position, `60FF` target velocity, `6071` target torque, `6060` mode selection, `60B8` touch probe function, `607F` max speed.
  - Manual (A6-EC ch8) says `0x1B02` (Input) fixed mapping contains: `603F` fault code, `6041` status word, `6064` position actual value, `6077` torque feedback, `6061` mode display, `60B9/60BA/60BC` touch probe status/edges, `60FD` DI status.
  - Manual: select the active RPDO via `0x1C12:01` and the active TPDO via `0x1C13:01` (one assignment each; choose from `0x1600/0x1701..0x1705` and `0x1A00/0x1B01..0x1B04` respectively).
  - Update (observed): `ethercat pdos -p0` reports the **default** SM2/SM3 assignment as `0x1701 / 0x1B01` (PP/CSP-oriented set).
  - Update (observed): CoE assignment objects can be set to `0x1702 / 0x1B02` via SDO writes to `0x1C12:01` and `0x1C13:01` (read-back confirms the new values), even if `ethercat pdos` continues to display the SII defaults.
- [ ] **Units of `0x6064/0x607A`**: are these raw encoder counts, or scaled “user units” due to electronic gearing (6091.*)?
- [ ] **Counts-per-rev / scaling**: confirm encoder resolution (position units) for the motor/drive combo (we used 131072 as a conservative placeholder for early tests).
  - ESI hint (StepperOnline A6-EC): `0x6081` default `0x001AAAAB` corresponds to ~50 rpm if velocity units are counts/s and \(counts\_per\_rev = 2{,}097{,}152\). `0x607F` default `0x06400000` then corresponds to 3000 rpm under the same assumption.
- [ ] **Sign conventions**: determine per-axis direction (does +command increase `0x6064`?).
- [ ] **DC/SYNC0 parameters**: confirm `assign_activate` and SYNC0 shift values for stable 1 kHz operation (we currently use a conservative default).
  - Manual (A6-EC ch8): the drive supports **DC sync only** (SYNC0-controlled). Sync cycle must be an integer multiple of **250 μs** (else `Er74.0`).
- [ ] **Fault/reset behavior**: confirm how A6‑EC behaves on faults and whether additional manufacturer-specific steps are needed beyond canonical DS402 sequences.
  - Update (implemented): RTCore now implements `CMD_FAULT_RESET(axis_mask)` and pulses DS402 controlword `0x0080` for a short window (still needs validation on real drives).
  - Manual (A6-EC ch10): EtherCAT config/sync related faults to watch for include `Er31.0` (PDO mapping objects >10), `Er32.1/Er32.5` (XML/ESI issues; check `U42.0B`), and `Er74.0/Er74.1/Er74.2` (DC/sync issues).
- [ ] **Avoid “big first step” faults**: confirm RTCore seeds/aligns `0x607A` to `0x6064` before enabling / switching modes, to avoid `Er87.1/Er87.2` (manual: excessive target position increment).

---

### RTCore implementation gaps / assumptions

- [ ] **Topology hash**: currently treated as 0 in early scaffolding; needs a real hash over the discovered identity tuple list.
- [ ] **Safety ladder**: watchdogs + safe-stop policy (WKC mismatch, OP loss, stale setpoint, etc.) are not production-complete yet.
- [ ] **Brake sequencing**: not implemented yet (and is axis/mechanical dependent).
- [ ] **Status fidelity**: in IPC-only mode the “pos_counts” were previously a synthetic echo; once EtherCAT is active it should always be real `0x6064`.
- [ ] **Telemetry/monitoring channel**: RTCore now emits `/run/gradient-rt-motion/metrics.json` for dashboards without consuming the single-client IPC slot (Sampler config in `scripts/sampler/`). Decide what the long-term “official” telemetry path is (IPC status ring extensions vs a metrics file).

---

### GradientOS integration uncertainties

- [ ] **Feedback conversion**: RTCore now publishes per-axis scaling via `MSG_STATUS_AXIS_CONFIG`, and the jog tool consumes it, but the Python `ethercat_rtcore` backend still returns “last setpoint” for `get_joint_positions()` (safe but not real feedback) until we implement counts→q conversion on the Python side.
- [ ] **Joint limit enforcement location**: decide what must be enforced in RTCore vs. what can remain in the Python layer (goal: safety-critical in RTCore).
- [ ] **Bring-up command path**: confirm which existing UDP commands you’ll use to drive J3/J4 (likely the low-level “6 angles” path) and ensure it doesn’t touch legacy serial paths.

