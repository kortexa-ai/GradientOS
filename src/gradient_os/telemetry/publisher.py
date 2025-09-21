import json
import socket
import time
from typing import Optional, Sequence


class UdpTelemetryPublisher:
    def __init__(self, target: str) -> None:
        host, port = target.rsplit(":", 1)
        self._addr = (host, int(port))
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def publish_state(self, joints_rad: Sequence[float], gripper: Optional[float] = None) -> None:
        msg = {"t": time.time(), "joints": [float(x) for x in joints_rad]}
        if gripper is not None:
            msg["gripper"] = float(gripper)
        self._sock.sendto(json.dumps(msg).encode("utf-8"), self._addr)

    def publish_action(self, action: Sequence[float]) -> None:
        msg = {"t": time.time(), "action": [float(x) for x in action]}
        self._sock.sendto(json.dumps(msg).encode("utf-8"), self._addr)


