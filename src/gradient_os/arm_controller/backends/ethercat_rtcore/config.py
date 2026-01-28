"""
Configuration shim for the `ethercat_rtcore` backend.

The RTOS/EtherCAT architecture removes serial-servos from the motion plane, but
some legacy modules still expect the "servo protocol constants" provided by an
active backend config module (see `utils._populate_servo_constants()`).

Until the old serial-only code paths are fully retired, we re-export the Feetech
constants as a compatibility layer so the controller can import/boot without
crashing when `--servo-backend ethercat_rtcore` is selected.

NOTE: These values are NOT used by RTCore and must not be relied on for EtherCAT
motion/limits. EtherCAT scaling lives in `/etc/gradient/ethercat.yaml` (RTCore).
"""

from ..feetech.config import *  # noqa: F401,F403

