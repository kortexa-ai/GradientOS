---
description: "Rules for integrating RTCore into existing GradientOS Python backend architecture."
alwaysApply: false
---

## Integration constraints (do not break)

- Python stays non-RT: API/UI/planning/trajectory generation only.
- RTCore is the only component that touches EtherCAT.

## Required integration shape

- Add Python backend package:
  - `src/gradient_os/arm_controller/backends/ethercat_rtcore/`
- Backend must be a proxy and follow the method-by-method behavior in plan section **15.11**.
- Select backend via `--servo-backend ethercat_rtcore` (or robot default).

## Critical migration rule

- When `ethercat_rtcore` backend is selected, the controller must **not** run Feetech serial initialization.
  - Gate the legacy servo init path in `gradient_os/run_controller.py`.

## Multi-axis + tool support

- RTCore axes are not limited to J1–J6; support E1–E3 + tool axes using `actuator_id == axis_index`.
- Do not model pneumatics/vacuum as “fake axes”; use `CMD_IO_WRITE` and `STATUS_IO_SNAPSHOT`.
