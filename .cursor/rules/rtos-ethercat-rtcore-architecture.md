---
description: "RTCore architecture + IPC rules: C++17 daemon, libecrt loop order, fixed IPC structs, safety invariants."
alwaysApply: false
---

## RTCore hard rules

- Implement RTCore as a **C++17 user-space daemon**: `gradient-rt-motion`.
- Link against **IgH `libecrt`**; RTCore owns the bus configuration and cyclic loop.
- One RT cyclic thread (SCHED_FIFO, CPU2–CPU3), one helper thread (CPU0–CPU1).
- No blocking syscalls, no dynamic allocation, no disk/network I/O in the RT loop.

## Cyclic loop ordering (must match the plan)

Each 1 kHz cycle:
1. `ecrt_master_receive()` + `ecrt_domain_process()`
2. read inputs (statusword, position, error code, DI)
3. update DS402 + watchdogs
4. compute outputs (controlword, mode, target position)
5. write outputs into process image
6. `ecrt_domain_queue()` + `ecrt_master_send()`
7. call application time + DC sync functions per cadence

## IPC (do not invent a new protocol)

- Use the IPC contract defined in `RTOS-ETHERCAT-PLAN/RTOS-ETHERCAT-plan.md` section **15.4**.
- Use `GRADIENT_MAX_AXES = 16`, ring msg size **512 bytes**.
- Motion setpoints use `SetpointSlotV1.q[]` (axis units per type: rad for revolute, m for prismatic).
- Non-motion EtherCAT I/O is controlled via `CMD_IO_WRITE` + `STATUS_IO_SNAPSHOT`.

## Safety invariants

- If topology hash mismatches expected: **refuse to arm**.
- If WKC mismatches expected in OP: safe stop ladder + disarm.
- If DC sync unstable: disarm.
- Stale setpoints: safe stop ladder + disarm.
