"""
ethercat_rtcore backend

This backend is a **proxy** to the RTCore daemon (`gradient-rt-motion`) described in:
- `RTOS-ETHERCAT-PLAN/RTOS-ETHERCAT-plan.md` §15

Python remains non-RT: it sends high-level setpoints and commands over IPC.
RTCore owns EtherCAT, DC/SYNC0, DS402, and all 1 kHz timing.
"""

from .backend import EthercatRTCoreBackend

__all__ = ["EthercatRTCoreBackend"]

