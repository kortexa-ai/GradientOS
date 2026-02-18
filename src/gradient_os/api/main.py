from __future__ import annotations

import asyncio
import base64
import binascii
import datetime
import json
import logging
import os
import socket
from contextlib import closing, asynccontextmanager
from typing import Any, Dict, Tuple

import argparse
import subprocess
import sys

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import numpy as np

from ..cad.topology_service import (
    CADTopologyService,
    TopologyDependencyError,
    TopologyModelNotFoundError,
)

try:
    from ..arm_controller import utils as controller_utils
    from ..arm_controller import command_api as controller_command_api
except ImportError:
    controller_utils = None
    controller_command_api = None

_REST_POSE_RAD = [0.0, -1.4, 1.5, 0.0, 0.0, 0.0]
_REST_POSE_COMMAND = ",".join(str(value) for value in _REST_POSE_RAD)
_ALLOWED_WELD_TYPES = {"fillet", "butt", "lap", "tack/spot", "custom"}
_PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_WELD_PROGRAM_DIR = os.path.join(_PROJECT_ROOT_DIR, "recorded_trajectories", "weld_programs")


def _default_controller_port() -> int:
    if controller_utils is not None:
        port = getattr(controller_utils, "UDP_PORT", None)
        if port is not None:
            return int(port)
    return 3000


def _resolve_controller_endpoint() -> Tuple[str, int]:
    host = os.environ.get("GRADIENT_CONTROLLER_HOST", "127.0.0.1")
    port = int(os.environ.get("GRADIENT_CONTROLLER_PORT", _default_controller_port()))
    return host, port


def _probe_controller(timeout: float = 0.5) -> Tuple[bool, str]:
    host, port = _resolve_controller_endpoint()
    payload = b"GET_STATUS"
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        sock.settimeout(max(0.05, timeout))
        try:
            sock.sendto(payload, (host, port))
            data, _addr = sock.recvfrom(1024)
        except socket.timeout:
            return False, f"Timed out waiting for controller response at {host}:{port}"
        except OSError as exc:
            return (
                False,
                f"Socket error connecting to controller at {host}:{port}: {exc}",
            )

    text = data.decode("utf-8", errors="ignore")
    if text.startswith("STATUS"):
        return True, f"Controller reachable at {host}:{port}"
    return False, f"Unexpected controller response '{text}' from {host}:{port}"


def _send_controller_command(
    message: str, timeout: float = 0.5, expect_response: bool = True
) -> Tuple[bool, str]:
    host, port = _resolve_controller_endpoint()
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        sock.settimeout(max(0.05, timeout))
        try:
            sock.sendto(message.encode("utf-8"), (host, port))
        except OSError as exc:
            return False, f"Socket error sending '{message}': {exc}"
        else:
            if not expect_response:
                return True, ""
        try:
            data, _addr = sock.recvfrom(1024)
        except socket.timeout:
            return False, f"No response for command '{message}'"
    text = data.decode("utf-8", errors="ignore")
    if text.startswith("ERROR"):
        return False, text
    return True, text


def _resolve_cors_origins() -> list[str]:
    raw = os.environ.get("GRADIENT_API_CORS", "")
    if not raw:
        return ["*"]
    origins = [item.strip() for item in raw.split(",")]
    return [origin for origin in origins if origin]


def _normalize_weld_type(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if not value:
        return "fillet"
    if value == "spot":
        value = "tack/spot"
    if value not in _ALLOWED_WELD_TYPES:
        allowed = ", ".join(sorted(_ALLOWED_WELD_TYPES))
        raise HTTPException(status_code=400, detail=f"Invalid weld_type '{value}'. Allowed: {allowed}")
    return value


def _decode_base64_step_payload(payload: dict[str, Any]) -> tuple[str, bytes]:
    filename_raw = payload.get("filename")
    filename = str(filename_raw).strip() if isinstance(filename_raw, str) else ""
    if not filename:
        filename = "uploaded.step"

    encoded = payload.get("step_base64")
    if not isinstance(encoded, str) or not encoded.strip():
        encoded = payload.get("step_data_base64")
    if not isinstance(encoded, str) or not encoded.strip():
        raise HTTPException(status_code=400, detail="Field 'step_base64' is required.")

    try:
        raw_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 STEP payload: {exc}") from exc
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Decoded STEP payload is empty.")
    return filename, raw_bytes


def _ensure_weld_program_dir() -> None:
    os.makedirs(_WELD_PROGRAM_DIR, exist_ok=True)


def _sanitize_weld_program_name(raw: Any) -> str:
    if not isinstance(raw, str):
        raise HTTPException(status_code=400, detail="Field 'name' must be a string.")
    trimmed = raw.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="Field 'name' is required.")
    safe = "".join(ch if (ch.isalnum() or ch in {"-", "_"}) else "_" for ch in trimmed)
    safe = safe.strip("_")
    if not safe:
        raise HTTPException(status_code=400, detail="Field 'name' must contain letters or numbers.")
    return safe[:128]


def _coerce_step_transform(raw: Any) -> dict[str, Any]:
    default = {
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotationDeg": {"x": 0.0, "y": 0.0, "z": 0.0},
        "scale": 1.0,
    }
    if not isinstance(raw, dict):
        return default

    def _axis_triplet(value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {"x": 0.0, "y": 0.0, "z": 0.0}
        out = {}
        for axis in ("x", "y", "z"):
            try:
                out[axis] = float(value.get(axis, 0.0))
            except Exception:
                out[axis] = 0.0
        return out

    try:
        scale = max(1e-4, float(raw.get("scale", 1.0)))
    except Exception:
        scale = 1.0

    return {
        "position": _axis_triplet(raw.get("position")),
        "rotationDeg": _axis_triplet(raw.get("rotationDeg")),
        "scale": scale,
    }


class _TelemetryProtocol(asyncio.DatagramProtocol):
    def __init__(self, hub: "TelemetryHub") -> None:
        self.hub = hub

    def datagram_received(self, data: bytes, addr) -> None:  # type: ignore[override]
        self.hub.handle_datagram(data, addr)


class TelemetryHub:
    def __init__(self) -> None:
        self._subscribers: Dict[int, asyncio.Queue[str]] = {}
        self._counter = 0
        self._lock = asyncio.Lock()
        self._transport: asyncio.DatagramTransport | None = None
        self._aux_transport: asyncio.DatagramTransport | None = None
        self._servo_proc: subprocess.Popen | None = None
        self._advertise_host = os.environ.get("GRADIENT_MONITOR_HOST")
        self._bind_host = os.environ.get("GRADIENT_MONITOR_BIND", "127.0.0.1")
        self._listen_port: int | None = None
        # Optional fixed UDP port to ingest auxiliary telemetry (e.g., servo_telemetry_stream.py)
        # Set GRADIENT_AUX_TELEMETRY_PORT=0 to disable. Default 5556.
        try:
            self._aux_listen_port: int | None = int(os.environ.get("GRADIENT_AUX_TELEMETRY_PORT", "5556"))
        except ValueError:
            self._aux_listen_port = 5556
        # Autostart the servo telemetry streamer (default DISABLED; set to 1/true to enable)
        _auto_env = os.environ.get("GRADIENT_AUTOSTART_SERVO_TELEMETRY", "0").strip().lower()
        self._autostart_servo_telemetry: bool = _auto_env in {"1", "true", "yes", "on"}

    async def register(self) -> Tuple[int, asyncio.Queue[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=50)
        async with self._lock:
            first_client = not self._subscribers
            if first_client:
                await self._start()
            self._counter += 1
            token = self._counter
            self._subscribers[token] = queue
        return token, queue

    async def unregister(self, token: int) -> None:
        async with self._lock:
            self._subscribers.pop(token, None)
            if not self._subscribers:
                await self._stop()

    async def _start(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _protocol = await loop.create_datagram_endpoint(
            lambda: _TelemetryProtocol(self),
            local_addr=(self._bind_host, 0),
        )
        self._transport = transport
        sockname = transport.get_extra_info("sockname")
        assert sockname is not None
        listen_host = self._advertise_host or _resolve_controller_endpoint()[0]
        self._listen_port = sockname[1]
        start_cmd = f"START_TELEMETRY,{listen_host}:{self._listen_port},10"
        ok, detail = await run_in_threadpool(_send_controller_command, start_cmd)
        if not ok:
            await self._cleanup_transport()
            raise HTTPException(status_code=503, detail=detail)
        # Optionally also open a fixed auxiliary UDP port to ingest extra telemetry sources.
        if self._aux_listen_port and self._aux_listen_port > 0:
            try:
                aux_transport, _aux_proto = await loop.create_datagram_endpoint(
                    lambda: _TelemetryProtocol(self),
                    local_addr=(self._bind_host, self._aux_listen_port),
                )
                self._aux_transport = aux_transport
            except Exception:
                # If aux port binding fails, continue without it.
                self._aux_transport = None
        # Autostart the servo telemetry streamer so charts work by default
        if self._autostart_servo_telemetry and self._aux_listen_port and self._aux_listen_port > 0:
            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "gradient_os.telemetry.servo_telemetry_stream",
                    "--fps",
                    "10",
                    "--udp",
                    f"127.0.0.1:{self._aux_listen_port}",
                ]
                self._servo_proc = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True
                )
            except Exception:
                self._servo_proc = None

    async def _stop(self) -> None:
        if self._listen_port is None:
            return
        stop_cmd = "STOP_TELEMETRY"
        await run_in_threadpool(_send_controller_command, stop_cmd)
        await self._cleanup_transport()

    async def _cleanup_transport(self) -> None:
        if self._transport is not None:
            self._transport.close()
        self._transport = None
        if self._aux_transport is not None:
            try:
                self._aux_transport.close()
            except Exception:
                pass
        self._aux_transport = None
        # Stop autostarted servo telemetry if running
        if self._servo_proc is not None:
            try:
                self._servo_proc.terminate()
            except Exception:
                pass
            self._servo_proc = None
        self._listen_port = None

    def handle_datagram(self, data: bytes, addr) -> None:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return
        event_payload = self._format_event(text)
        for queue in list(self._subscribers.values()):
            try:
                queue.put_nowait(event_payload)
            except asyncio.QueueFull:
                try:
                    _ = queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(event_payload)
                except asyncio.QueueFull:
                    # If still full, skip this subscriber to avoid blocking.
                    continue

    def _format_event(self, text: str) -> str:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        return json.dumps(parsed)


telemetry_hub = TelemetryHub()
topology_service = CADTopologyService()
logger = logging.getLogger("uvicorn.error")
_latest_plan_lock = asyncio.Lock()
_latest_plan: dict[str, Any] | None = None


def create_app() -> FastAPI:
    def _resolve_rest_pose() -> list[float]:
        raw = os.environ.get("GRADIENT_REST_POSE", "").strip()
        if raw:
            try:
                vals = [float(tok) for tok in raw.split(",") if tok.strip() != ""]
                # Expect 6 values; if not, still return what we have rather than crash
                return vals
            except Exception:
                pass
        # Fallback to the desktop UI default (radians)
        return [0.0, -1.4, 1.5, 0.0, 0.0, 0.0]
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ok, detail = await run_in_threadpool(_probe_controller)
        host, port = _resolve_controller_endpoint()
        if ok:
            logger.info("Controller: %s:%s", host, port)
        else:
            logger.warning("Controller: %s:%s (%s)", host, port, detail)
        yield

    api = FastAPI(title="GradientOS API", version="0.1.0", lifespan=lifespan)
    origins = _resolve_cors_origins()
    allow_credentials = "*" not in origins
    api.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=allow_credentials,
    )

    @api.get("/health", summary="Controller health probe")
    async def health():
        ok, detail = await run_in_threadpool(_probe_controller)
        if not ok:
            raise HTTPException(status_code=503, detail=detail)
        host, port = _resolve_controller_endpoint()
        return {
            "status": "ok",
            "detail": detail,
            "controller": {"host": host, "port": port},
        }

    def _controller_call_or_503(
        command: str, *, timeout: float = 0.5, expect_response: bool = True
    ) -> str:
        ok, detail = _send_controller_command(
            command, timeout=timeout, expect_response=expect_response
        )
        if not ok:
            raise HTTPException(status_code=503, detail=detail)
        return detail

    def _parse_bool_token(token: str) -> bool:
        return token.strip().lower() in {"1", "true", "yes", "on"}

    @api.post("/control/stop", summary="Emergency stop")
    async def control_stop():
        detail = await run_in_threadpool(
            _controller_call_or_503, "STOP", timeout=1.0, expect_response=True
        )
        return {"status": "ok", "detail": detail}

    @api.post("/control/wait-for-idle", summary="Block until motion completes")
    async def control_wait_for_idle():
        detail = await run_in_threadpool(
            _controller_call_or_503, "WAIT_FOR_IDLE", timeout=60.0, expect_response=True
        )
        return {"status": "ok", "detail": detail}

    @api.post("/control/home", summary="Move all joints to zero position")
    async def control_home():
        await run_in_threadpool(
            _controller_call_or_503, "0,0,0,0,0,0", timeout=2.0, expect_response=False
        )
        return {"status": "ok"}

    @api.post("/control/rest", summary="Move all joints to predefined REST pose")
    async def control_rest():
        pose_cmd = ",".join(map(str, _resolve_rest_pose()))
        await run_in_threadpool(
            _controller_call_or_503, pose_cmd, timeout=2.0, expect_response=False
        )
        return {"status": "ok"}

    @api.post("/control/move-line-relative", summary="Move tool by dx,dy,dz with optional speed multiplier")
    async def control_move_line_relative(payload: dict[str, Any]):
        try:
            dx = float(payload.get("dx", 0.0))
            dy = float(payload.get("dy", 0.0))
            dz = float(payload.get("dz", 0.0))
        except Exception:
            raise HTTPException(status_code=400, detail="dx, dy, dz must be numbers")
        speed_multiplier = payload.get("speed_multiplier", None)
        try:
            sm = float(speed_multiplier) if speed_multiplier is not None else None
        except Exception:
            raise HTTPException(status_code=400, detail="speed_multiplier must be a number")
        closed = bool(payload.get("closed", True))
        # Command format: MOVE_LINE_RELATIVE,dx,dy,dz[,speed_multiplier][,closed]
        parts: list[str] = [
            "MOVE_LINE_RELATIVE",
            str(dx),
            str(dy),
            str(dz),
        ]
        if sm is not None:
            parts.append(str(sm))
        parts.append("true" if closed else "false")
        cmd = ",".join(parts)
        await run_in_threadpool(_controller_call_or_503, cmd, timeout=2.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/rotate", summary="Rotate tool by axis and angle in degrees (relative)")
    async def control_rotate(payload: dict[str, Any]):
        axis_in = str(payload.get("axis", "")).strip().lower()
        # Accept multiple synonyms and normalize to scipy-euler tokens: x/y/z
        axis_map = {
            "roll": "x", "r": "x", "x": "x",
            "pitch": "y", "p": "y", "y": "y",
            "yaw": "z", "w": "z", "z": "z",
        }
        axis = axis_map.get(axis_in)
        if axis is None:
            raise HTTPException(status_code=400, detail="axis must be one of roll,pitch,yaw (or x/y/z)")
        try:
            angle_deg = float(payload.get("angle_deg", 0.0))
        except Exception:
            raise HTTPException(status_code=400, detail="angle_deg must be a number")
        # Emulate desktop UI: fetch current absolute RPY, then call SET_ORIENTATION with updated axis
        detail = await run_in_threadpool(_controller_call_or_503, "GET_POSITION", timeout=1.0)
        parts = detail.split(",")
        if len(parts) < 1 or parts[0] != "CURRENT_POSE" or len(parts) < 1 + 3 + 3:
            raise HTTPException(status_code=502, detail=f"Malformed pose reply: {detail}")
        try:
            orient = list(map(float, parts[4:7]))  # roll, pitch, yaw in degrees
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"Invalid orientation data: {exc}") from exc
        # Update selected axis
        if axis == "x":
            orient[0] += angle_deg
        elif axis == "y":
            orient[1] += angle_deg
        else:
            orient[2] += angle_deg
        set_cmd = f"SET_ORIENTATION,{orient[0]},{orient[1]},{orient[2]}"
        await run_in_threadpool(_controller_call_or_503, set_cmd, timeout=2.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/set-orientation", summary="Set absolute end-effector orientation (roll,pitch,yaw deg)")
    async def control_set_orientation(payload: dict[str, Any]):
        try:
            roll = float(payload.get("roll", 0.0))
            pitch = float(payload.get("pitch", 0.0))
            yaw = float(payload.get("yaw", 0.0))
        except Exception:
            raise HTTPException(status_code=400, detail="roll,pitch,yaw must be numbers")
        cmd = f"SET_ORIENTATION,{roll},{pitch},{yaw}"
        await run_in_threadpool(_controller_call_or_503, cmd, timeout=2.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/set-gripper", summary="Set gripper angle in degrees")
    async def control_set_gripper(payload: dict[str, Any]):
        try:
            angle = float(payload.get("angle_deg", 0.0))
        except Exception:
            raise HTTPException(status_code=400, detail="angle_deg must be a number")
        cmd = f"SET_GRIPPER,{angle}"
        await run_in_threadpool(_controller_call_or_503, cmd, timeout=1.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/jog/start", summary="Begin realtime jog mode")
    async def control_jog_start():
        await run_in_threadpool(_controller_call_or_503, "JOG_START", timeout=1.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/jog/stop", summary="Stop realtime jog mode")
    async def control_jog_stop():
        await run_in_threadpool(_controller_call_or_503, "JOG_STOP", timeout=1.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/jog/velocity", summary="Set realtime jog velocity vector")
    async def control_jog_velocity(payload: dict[str, Any]):
        def _num(name: str) -> float:
            try:
                return float(payload.get(name, 0.0))
            except Exception:
                raise HTTPException(status_code=400, detail=f"{name} must be a number")
        vx = _num("vx"); vy = _num("vy"); vz = _num("vz")
        v_roll = _num("v_roll"); v_pitch = _num("v_pitch"); v_yaw = _num("v_yaw")
        cmd = f"SET_JOG_VELOCITY,{vx},{vy},{vz},{v_roll},{v_pitch},{v_yaw}"
        await run_in_threadpool(_controller_call_or_503, cmd, timeout=1.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/jog/deadman", summary="Enable/disable jog deadman")
    async def control_jog_deadman(payload: dict[str, Any]):
        enabled = bool(payload.get("enabled", True))
        cmd = f"SET_JOG_DEADMAN,{'true' if enabled else 'false'}"
        await run_in_threadpool(_controller_call_or_503, cmd, timeout=1.0, expect_response=False)
        return {"status": "ok"}

    @api.post("/control/jog/debug", summary="Enable/disable jog debug logging")
    async def control_jog_debug(payload: dict[str, Any]):
        enabled = bool(payload.get("enabled", False))
        cmd = f"SET_JOG_DEBUG,{'true' if enabled else 'false'}"
        await run_in_threadpool(_controller_call_or_503, cmd, timeout=1.0, expect_response=False)
        return {"status": "ok"}

    @api.get("/info/status", summary="Controller status snapshot")
    async def info_status():
        detail = await run_in_threadpool(_controller_call_or_503, "GET_STATUS")
        parts = detail.split(",")
        if len(parts) != 3 or parts[0] != "STATUS":
            raise HTTPException(status_code=502, detail=f"Malformed status reply: {detail}")
        return {"gripper_present": _parse_bool_token(parts[2])}

    @api.get("/info/pose", summary="Current tool pose and joint angles")
    async def info_pose():
        detail = await run_in_threadpool(_controller_call_or_503, "GET_POSITION", timeout=1.0)
        parts = detail.split(",")
        if len(parts) < 1 or parts[0] != "CURRENT_POSE" or len(parts) < 1 + 3 + 3:
            raise HTTPException(status_code=502, detail=f"Malformed pose reply: {detail}")
        try:
            pos = list(map(float, parts[1:4]))
            orient = list(map(float, parts[4:7]))
            joint_vals = list(map(float, parts[7:]))
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"Invalid pose data: {exc}") from exc
        return {
            "position_m": {"x": pos[0], "y": pos[1], "z": pos[2]},
            "orientation_euler_deg": {"roll": orient[0], "pitch": orient[1], "yaw": orient[2]},
            "joints_deg": joint_vals,
        }

    @api.get("/info/orientation", summary="Current end-effector orientation matrix")
    async def info_orientation():
        detail = await run_in_threadpool(_controller_call_or_503, "GET_ORIENTATION", timeout=1.0)
        parts = detail.split(",")
        if not parts or parts[0] != "CURRENT_ORIENTATION" or len(parts) != 10:
            raise HTTPException(status_code=502, detail=f"Malformed orientation reply: {detail}")
        try:
            matrix_values = list(map(float, parts[1:]))
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"Invalid orientation data: {exc}") from exc
        return {
            "matrix": [
                matrix_values[0:3],
                matrix_values[3:6],
                matrix_values[6:9],
            ]
        }

    @api.get("/info/joints", summary="Current joint angles")
    async def info_joints():
        detail = await run_in_threadpool(_controller_call_or_503, "GET_JOINT_ANGLES")
        parts = detail.split(",")
        if not parts or parts[0] != "JOINT_ANGLES":
            raise HTTPException(status_code=502, detail=f"Malformed joint reply: {detail}")
        try:
            angles = list(map(float, parts[1:]))
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"Invalid joint data: {exc}") from exc
        arm = angles[:6]
        gripper = angles[6] if len(angles) > 6 else None
        payload = {"arm_deg": arm}
        if gripper is not None:
            payload["gripper_deg"] = gripper
        return payload

    @api.get("/info/gripper", summary="Gripper angle snapshot")
    async def info_gripper():
        detail = await run_in_threadpool(_controller_call_or_503, "GET_GRIPPER_STATE")
        parts = detail.split(",")
        if len(parts) != 3 or parts[0] != "GRIPPER_STATE":
            raise HTTPException(status_code=502, detail=f"Malformed gripper reply: {detail}")
        try:
            angle_deg = float(parts[1])
            raw = int(float(parts[2]))
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"Invalid gripper data: {exc}") from exc
        return {"angle_deg": angle_deg, "raw_position": raw}

    @api.get("/info/all-positions", summary="Raw servo positions")
    async def info_all_positions():
        detail = await run_in_threadpool(
            _controller_call_or_503, "GET_ALL_POSITIONS", timeout=1.0
        )
        parts = detail.split(",")
        if not parts or parts[0] != "ALL_POS_DATA" or len(parts) < 3:
            raise HTTPException(status_code=502, detail=f"Malformed positions reply: {detail}")
        if (len(parts) - 1) % 2 != 0:
            raise HTTPException(status_code=502, detail=f"Unexpected positions payload: {detail}")
        payload = []
        for i in range(1, len(parts), 2):
            servo_id = parts[i]
            position = parts[i + 1]
            try:
                servo_id_int = int(servo_id)
            except ValueError:
                servo_id_int = servo_id  # fall back to raw string if malformed
            try:
                position_int: int | None = None if position == "FAIL" else int(position)
            except ValueError:
                position_int = None
            payload.append({"servo_id": servo_id_int, "raw_position": position_int})
        return {"servos": payload}

    @api.get("/monitor", summary="Subscribe to controller telemetry stream")
    async def monitor():
        token, queue = await telemetry_hub.register()

        async def event_generator():
            try:
                while True:
                    message = await queue.get()
                    yield message
            except asyncio.CancelledError:
                raise
            finally:
                await telemetry_hub.unregister(token)

        return EventSourceResponse(event_generator(), ping=15)

    @api.post("/cad/topology/load-step", summary="Load STEP topology from exact CAD edges")
    async def cad_topology_load_step(payload: dict[str, Any]):
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required.")
        filename, step_bytes = _decode_base64_step_payload(payload)
        sample_count = payload.get("sample_count", 64)
        try:
            sample_count_int = int(sample_count)
        except Exception:
            raise HTTPException(status_code=400, detail="sample_count must be an integer")

        def _load():
            return topology_service.load_step(
                filename=filename,
                step_bytes=step_bytes,
                sample_count=sample_count_int,
            )

        try:
            return await run_in_threadpool(_load)
        except TopologyDependencyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Topology extraction failed: {exc}") from exc

    @api.get("/cad/topology/{model_id}", summary="Fetch topology edges for a loaded STEP model")
    async def cad_topology_detail(model_id: str):
        try:
            return topology_service.get_model(model_id)
        except TopologyModelNotFoundError:
            raise HTTPException(status_code=404, detail=f"Unknown topology model '{model_id}'.")

    @api.post("/weld-program/save", summary="Save weld program with embedded STEP payload")
    async def weld_program_save(payload: dict[str, Any]):
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required.")

        safe_name = _sanitize_weld_program_name(payload.get("name"))
        step_payload = payload.get("step")
        if not isinstance(step_payload, dict):
            raise HTTPException(status_code=400, detail="Field 'step' is required and must be an object.")
        step_filename, step_bytes = _decode_base64_step_payload(step_payload)
        step_base64 = base64.b64encode(step_bytes).decode("ascii")
        step_transform = _coerce_step_transform(step_payload.get("transform"))

        weld_draft_raw = payload.get("weld_draft")
        if not isinstance(weld_draft_raw, dict):
            raise HTTPException(status_code=400, detail="Field 'weld_draft' is required and must be an object.")

        default_weld_type = _normalize_weld_type(
            weld_draft_raw.get("weldType", weld_draft_raw.get("weld_type", "fillet"))
        )
        segments: list[dict[str, Any]] = []
        raw_segments = weld_draft_raw.get("segments")
        if isinstance(raw_segments, list):
            seen_edge_ids: set[str] = set()
            for raw_segment in raw_segments:
                if not isinstance(raw_segment, dict):
                    continue
                edge_id = str(
                    raw_segment.get("edgeId", raw_segment.get("edge_id", ""))
                ).strip()
                if not edge_id or edge_id in seen_edge_ids:
                    continue
                try:
                    start_s = float(raw_segment.get("startS", raw_segment.get("start_s", 0.0)))
                except (TypeError, ValueError):
                    start_s = 0.0
                try:
                    end_s = float(raw_segment.get("endS", raw_segment.get("end_s", 1.0)))
                except (TypeError, ValueError):
                    end_s = 1.0
                start_s = max(0.0, min(1.0, start_s))
                end_s = max(0.0, min(1.0, end_s))
                weld_type = _normalize_weld_type(
                    raw_segment.get("weldType", raw_segment.get("weld_type", default_weld_type))
                )
                segments.append(
                    {
                        "edgeId": edge_id,
                        "startS": start_s,
                        "endS": end_s,
                        "weldType": weld_type,
                    }
                )
                seen_edge_ids.add(edge_id)

        legacy_edge_id = str(weld_draft_raw.get("edgeId", weld_draft_raw.get("edge_id", ""))).strip()
        try:
            legacy_start_s = float(weld_draft_raw.get("startS", weld_draft_raw.get("start_s", 0.0)))
        except (TypeError, ValueError):
            legacy_start_s = 0.0
        try:
            legacy_end_s = float(weld_draft_raw.get("endS", weld_draft_raw.get("end_s", 1.0)))
        except (TypeError, ValueError):
            legacy_end_s = 1.0
        legacy_start_s = max(0.0, min(1.0, legacy_start_s))
        legacy_end_s = max(0.0, min(1.0, legacy_end_s))
        if not segments and legacy_edge_id:
            segments.append(
                {
                    "edgeId": legacy_edge_id,
                    "startS": legacy_start_s,
                    "endS": legacy_end_s,
                    "weldType": default_weld_type,
                }
            )

        requested_active_edge_id = str(
            weld_draft_raw.get(
                "activeSegmentEdgeId",
                weld_draft_raw.get("active_segment_edge_id", legacy_edge_id),
            )
        ).strip()
        active_segment_edge_id = (
            requested_active_edge_id
            if requested_active_edge_id and any(seg["edgeId"] == requested_active_edge_id for seg in segments)
            else (segments[0]["edgeId"] if segments else "")
        )
        active_segment = next(
            (seg for seg in segments if seg["edgeId"] == active_segment_edge_id),
            segments[0] if segments else None,
        )
        active_weld_type = (
            _normalize_weld_type(active_segment.get("weldType", default_weld_type))
            if isinstance(active_segment, dict)
            else default_weld_type
        )
        post_action_raw = str(
            weld_draft_raw.get("postAction", weld_draft_raw.get("post_action", "return_to_start"))
        ).strip()
        post_action = (
            "none"
            if post_action_raw == "none"
            else ("lift" if post_action_raw == "lift" else "return_to_start")
        )

        weld_draft = {
            "modelId": str(weld_draft_raw.get("modelId", weld_draft_raw.get("model_id", ""))).strip(),
            "edgeId": active_segment["edgeId"] if active_segment else legacy_edge_id,
            "weldType": active_weld_type,
            "weldName": str(weld_draft_raw.get("weldName", weld_draft_raw.get("weld_name", f"{active_weld_type} weld"))).strip() or f"{active_weld_type} weld",
            "workAngleDeg": float(weld_draft_raw.get("workAngleDeg", weld_draft_raw.get("work_angle_deg", 45.0))),
            "travelAngleDeg": float(weld_draft_raw.get("travelAngleDeg", weld_draft_raw.get("travel_angle_deg", 0.0))),
            "transitionClearanceMm": float(
                weld_draft_raw.get("transitionClearanceMm", weld_draft_raw.get("transition_clearance_mm", 35.0))
            ),
            "postAction": post_action,
            "startS": active_segment["startS"] if active_segment else legacy_start_s,
            "endS": active_segment["endS"] if active_segment else legacy_end_s,
            "segments": segments,
            "activeSegmentEdgeId": active_segment_edge_id or None,
        }

        editable_waypoints = [
            {"x": x, "y": y, "z": z}
            for (x, y, z) in _coerce_waypoint_list(payload.get("editable_waypoints"))
        ]

        planned_trajectory = payload.get("planned_trajectory")
        if planned_trajectory is not None and not isinstance(planned_trajectory, dict):
            raise HTTPException(status_code=400, detail="planned_trajectory must be an object or null.")

        record: dict[str, Any] = {
            "name": safe_name,
            "saved_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "step": {
                "filename": step_filename,
                "step_base64": step_base64,
                "transform": step_transform,
            },
            "weld_draft": weld_draft,
            "editable_waypoints": editable_waypoints,
            "planned_trajectory": planned_trajectory,
        }

        _ensure_weld_program_dir()
        path = os.path.join(_WELD_PROGRAM_DIR, f"{safe_name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        return {"status": "ok", "name": safe_name}

    @api.get("/weld-program/list", summary="List saved weld programs")
    async def weld_program_list():
        _ensure_weld_program_dir()
        names: list[str] = []
        for filename in os.listdir(_WELD_PROGRAM_DIR):
            if not filename.lower().endswith(".json"):
                continue
            names.append(filename[:-5])
        names.sort()
        return {"programs": names}

    @api.get("/weld-program/{name}", summary="Load a saved weld program")
    async def weld_program_detail(name: str):
        safe_name = _sanitize_weld_program_name(name)
        path = os.path.join(_WELD_PROGRAM_DIR, f"{safe_name}.json")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Weld program '{safe_name}' not found.")
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load weld program: {exc}") from exc
        return payload

    @api.post("/trajectory/plan", summary="Begin recording a new trajectory")
    async def trajectory_plan():
        await run_in_threadpool(
            _controller_call_or_503,
            "PLAN_TRAJECTORY",
            timeout=1.0,
            expect_response=False,
        )
        return {"status": "ok"}

    @api.post("/trajectory/record", summary="Record current pose into active trajectory")
    async def trajectory_record():
        await run_in_threadpool(
            _controller_call_or_503, "REC_POS", timeout=1.0, expect_response=False
        )
        return {"status": "ok"}

    @api.post("/trajectory/end", summary="Finish trajectory recording and save by name")
    async def trajectory_end(payload: dict):
        name = (payload or {}).get("name")
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="Field 'name' is required.")
        command = f"END_TRAJECTORY,{name.strip()}"
        await run_in_threadpool(
            _controller_call_or_503, command, timeout=2.0, expect_response=False
        )
        return {"status": "ok", "name": name.strip()}

    @api.post("/trajectory/plan-points", summary="Plan joint path for custom Cartesian way-points")
    async def trajectory_plan_points(payload: dict):
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required.")
        points = _coerce_waypoint_list(payload.get("points"))
        if not points:
            raise HTTPException(status_code=400, detail="Field 'points' must contain at least one waypoint.")

        coord_tokens = ",".join(str(value) for point in points for value in point)
        command = "PLAN_TRAJECTORY_POINTS," + coord_tokens
        detail = await run_in_threadpool(
            _controller_call_or_503, command, timeout=2.0, expect_response=True
        )
        prefix = "PLANNED_TRAJECTORY_POINTS,"
        if not detail.startswith(prefix):
            raise HTTPException(status_code=502, detail=f"Malformed planner reply: {detail}")
        try:
            payload_dict = json.loads(detail[len(prefix) :])
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail=f"Planner payload decode failure: {exc}") from exc
        return payload_dict

    @api.post("/trajectory/plan-weld", summary="Plan a weld trajectory from selected CAD edge segment")
    async def trajectory_plan_weld(payload: dict[str, Any]):
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required.")
        if controller_command_api is None:
            raise HTTPException(status_code=500, detail="Arm controller command API unavailable")

        model_id = payload.get("model_id")
        edge_id = payload.get("edge_id")
        if not isinstance(model_id, str) or not model_id.strip():
            raise HTTPException(status_code=400, detail="Field 'model_id' is required.")
        if not isinstance(edge_id, str) or not edge_id.strip():
            raise HTTPException(status_code=400, detail="Field 'edge_id' is required.")

        try:
            start_s = float(payload.get("start_s", 0.0))
            end_s = float(payload.get("end_s", 1.0))
        except Exception:
            raise HTTPException(status_code=400, detail="start_s and end_s must be numbers in [0, 1].")
        sample_count_raw = payload.get("sample_count", 40)
        try:
            sample_count = max(2, int(sample_count_raw))
        except Exception:
            raise HTTPException(status_code=400, detail="sample_count must be an integer.")

        weld_type = _normalize_weld_type(payload.get("weld_type", "fillet"))
        weld_name_raw = payload.get("weld_name")
        weld_name = str(weld_name_raw).strip() if isinstance(weld_name_raw, str) else ""
        if not weld_name:
            weld_name = f"{weld_type} weld"

        waypoints_override = _coerce_waypoint_list(payload.get("waypoints_override"))
        sections = _coerce_plan_sections(payload.get("sections"))
        preview_name_raw = payload.get("preview_name")
        preview_name = (
            str(preview_name_raw).strip()
            if isinstance(preview_name_raw, str) and preview_name_raw.strip()
            else getattr(controller_command_api, "WELD_PREVIEW_NAME", "__weld_preview__")
        )

        weld_options = payload.get("options")
        if weld_options is None:
            weld_options = {}
        elif not isinstance(weld_options, dict):
            raise HTTPException(status_code=400, detail="options must be an object.")
        post_action_raw = str(weld_options.get("post_action", "return_to_start")).strip()
        weld_options["post_action"] = (
            "none"
            if post_action_raw == "none"
            else ("lift" if post_action_raw == "lift" else "return_to_start")
        )

        if sections:
            weld_points = [
                [float(point[0]), float(point[1]), float(point[2])]
                for section in sections
                for point in section["points"]
            ]
            sampled_start = max(0.0, min(1.0, start_s))
            sampled_end = max(0.0, min(1.0, end_s))
        elif waypoints_override:
            weld_points = [list(point) for point in waypoints_override]
            sampled_start = max(0.0, min(1.0, start_s))
            sampled_end = max(0.0, min(1.0, end_s))
        else:
            try:
                sampled = topology_service.sample_edge_segment(
                    model_id=model_id.strip(),
                    edge_id=edge_id.strip(),
                    start_s=start_s,
                    end_s=end_s,
                    sample_count=sample_count,
                )
            except TopologyModelNotFoundError:
                raise HTTPException(status_code=404, detail=f"Unknown topology model '{model_id}'.")
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            weld_points = [[float(p[0]), float(p[1]), float(p[2])] for p in sampled]
            sampled_start = max(0.0, min(1.0, start_s))
            sampled_end = max(0.0, min(1.0, end_s))

        weld_metadata = {
            "type": weld_type,
            "name": weld_name,
            "model_id": model_id.strip(),
            "edge_id": edge_id.strip(),
            "start_s": sampled_start,
            "end_s": sampled_end,
            "options": weld_options,
        }

        def _plan():
            live_joints = _get_live_joint_angles_from_controller(timeout=1.0)
            if controller_utils is not None:
                controller_utils.current_logical_joint_angles_rad = list(live_joints)
            if hasattr(controller_command_api, "utils"):
                controller_command_api.utils.current_logical_joint_angles_rad = list(live_joints)
            return controller_command_api.plan_preview_trajectory_points(
                weld_points,
                preview_name=preview_name,
                weld_metadata=weld_metadata,
                sections=sections if sections else None,
            )

        try:
            result = await run_in_threadpool(_plan)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=f"Weld planning failed: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Weld planning failed unexpectedly: {exc}") from exc

        result["source"] = {
            "mode": "sections" if sections else ("waypoints_override" if waypoints_override else "edge_segment"),
            "sample_count": len(weld_points),
            "section_count": len(sections) if sections else 0,
        }
        return result

    @api.get("/trajectory/detail/{name}", summary="Fetch the definition of a recorded trajectory")
    async def trajectory_detail(name: str):
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="Trajectory name is required.")

        def _load() -> dict[str, Any] | None:
            if controller_command_api is None:
                raise RuntimeError("Arm controller command API unavailable")
            return controller_command_api._load_trajectory_by_name(name.strip())

        try:
            trajectory = await run_in_threadpool(_load)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if trajectory is None:
            raise HTTPException(status_code=404, detail=f"Trajectory '{name}' not found.")
        return {"name": name.strip(), "trajectory": trajectory}

    @api.get("/trajectory/list", summary="List available recorded trajectories")
    async def trajectory_list():
        detail = await run_in_threadpool(_controller_call_or_503, "GET_TRAJECTORIES")
        parts = detail.split(",")
        if not parts or parts[0] != "TRAJECTORIES":
            raise HTTPException(status_code=502, detail=f"Malformed trajectory list: {detail}")
        names = [name for name in parts[1:] if name]
        return {"trajectories": names}

    @api.post("/trajectory/run", summary="Execute a recorded trajectory")
    async def trajectory_run(payload: dict):
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body required.")
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="Field 'name' is required.")
        use_cache = payload.get("use_cache", False)
        loop_override = payload.get("loop_override")
        parts = [name.strip()]
        if isinstance(use_cache, bool):
            parts.append("true" if use_cache else "false")
        else:
            parts.append("" if use_cache is None else str(use_cache))
        if isinstance(loop_override, bool):
            parts.append("true" if loop_override else "false")
        elif loop_override is not None:
            parts.append(str(loop_override))
        command = "RUN_TRAJECTORY," + ",".join(parts)
        await run_in_threadpool(
            _controller_call_or_503, command, timeout=2.0, expect_response=False
        )
        return {"status": "ok"}

    @api.post("/trajectory/preview", summary="Plan a trajectory to a target point")
    async def trajectory_preview(payload: dict):
        plan = await _plan_point(payload)
        async with _latest_plan_lock:
            global _latest_plan
            _latest_plan = plan
        return plan

    @api.post("/trajectory/execute-preview", summary="Execute the last planned preview trajectory")
    async def trajectory_execute_preview():
        global _latest_plan
        async with _latest_plan_lock:
            plan = _latest_plan
        if plan is None:
            raise HTTPException(status_code=404, detail="No planned trajectory is available.")

        target = plan.get("target", {})
        try:
            x = float(target["x"])
            y = float(target["y"])
            z = float(target["z"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Stored plan is invalid.")

        velocity = float(plan.get("velocity", 0.1))
        acceleration = float(plan.get("acceleration", 0.05))
        closed_loop = bool(plan.get("closed_loop", True))
        closed_loop_token = "true" if closed_loop else "false"

        command = f"MOVE_LINE,{x},{y},{z},{velocity},{acceleration},{closed_loop_token}"
        await run_in_threadpool(
            _controller_call_or_503, command, timeout=5.0, expect_response=False
        )
        await run_in_threadpool(
            _controller_call_or_503, "WAIT_FOR_IDLE", timeout=60.0, expect_response=True
        )

        async with _latest_plan_lock:
            _latest_plan = None
        return {"status": "ok"}

    @api.post("/trajectory/clear-preview", summary="Discard the stored preview trajectory")
    async def trajectory_clear_preview():
        global _latest_plan
        async with _latest_plan_lock:
            _latest_plan = None
        return {"status": "ok"}

    return api


def _parse_pose_response(detail: str) -> list[float]:
    parts = detail.split(",")
    if len(parts) < 7 or parts[0] != "CURRENT_POSE":
        raise ValueError(f"Malformed pose reply: {detail}")
    try:
        joints = [float(value) for value in parts[7:]]
    except ValueError as exc:
        raise ValueError("Invalid joint data from controller") from exc
    return joints


def _coerce_waypoint_list(raw_points: Any) -> list[tuple[float, float, float]]:
    if not isinstance(raw_points, list):
        return []
    points: list[tuple[float, float, float]] = []
    for idx, entry in enumerate(raw_points):
        try:
            if isinstance(entry, dict):
                x = float(entry["x"])
                y = float(entry["y"])
                z = float(entry["z"])
            elif isinstance(entry, (list, tuple)) and len(entry) == 3:
                x, y, z = (float(entry[0]), float(entry[1]), float(entry[2]))
            else:
                raise ValueError("Waypoint must be an object with x/y/z or a 3-element list/tuple.")
        except (TypeError, ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid waypoint at index {idx}: {exc}"
            ) from exc
        points.append((x, y, z))
    return points


def _coerce_plan_sections(raw_sections: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_sections, list):
        return []
    sections: list[dict[str, Any]] = []
    for idx, raw_section in enumerate(raw_sections):
        if not isinstance(raw_section, dict):
            raise HTTPException(status_code=400, detail=f"Invalid section at index {idx}: expected object")
        kind_raw = str(raw_section.get("kind", "weld")).strip().lower()
        kind = "transition" if kind_raw == "transition" else "weld"
        points = _coerce_waypoint_list(raw_section.get("points"))
        if len(points) < 2:
            continue
        section: dict[str, Any] = {
            "kind": kind,
            "points": points,
        }
        weld_type_raw = raw_section.get("weld_type", raw_section.get("weldType"))
        if weld_type_raw is not None and str(weld_type_raw).strip():
            section["weld_type"] = _normalize_weld_type(weld_type_raw)
        edge_id_raw = raw_section.get("edge_id", raw_section.get("edgeId"))
        if isinstance(edge_id_raw, str) and edge_id_raw.strip():
            section["edge_id"] = edge_id_raw.strip()
        sections.append(section)
    return sections


def _get_live_joint_angles_from_controller(timeout: float = 1.0) -> list[float]:
    ok, detail = _send_controller_command("GET_POSITION", timeout=timeout)
    if not ok:
        raise HTTPException(status_code=503, detail=detail)
    try:
        joints = _parse_pose_response(detail)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if len(joints) == 0:
        raise HTTPException(status_code=502, detail="Controller returned no joint angles in pose reply.")
    return joints


async def _plan_point(payload: dict) -> dict[str, Any]:
    try:
        x = float(payload.get("x"))
        y = float(payload.get("y"))
        z = float(payload.get("z"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Fields 'x', 'y', 'z' are required floats")

    velocity = float(payload.get("velocity", 0.1))
    acceleration = float(payload.get("acceleration", 0.05))
    closed_loop = bool(payload.get("closed_loop", True))

    def _compute_plan() -> dict[str, Any]:
        start_joints = _get_live_joint_angles_from_controller(timeout=1.0)

        from ..arm_controller import trajectory_execution
        from .. import ik_solver

        target = np.array([x, y, z], dtype=float)
        path = trajectory_execution._plan_smooth_move(
            start_q=start_joints,
            target_pos=target,
            velocity=velocity,
            acceleration=acceleration,
            frequency=100,
            use_smoothing=True,
        )
        if not path:
            raise HTTPException(status_code=502, detail="Planner failed to produce a path")

        cartesian_points: list[list[float]] = []
        for joints in path:
            try:
                fk_point = ik_solver.get_fk(joints)
            except Exception:
                fk_point = None
            if fk_point is None:
                continue
            arr = np.asarray(fk_point, dtype=float)
            if arr.shape[0] >= 3:
                cartesian_points.append(arr[:3].tolist())

        return {
            "target": {"x": x, "y": y, "z": z},
            "velocity": velocity,
            "acceleration": acceleration,
            "closed_loop": closed_loop,
            "joints_rad": path,
            "cartesian_m": cartesian_points,
        }

    return await run_in_threadpool(_compute_plan)


app = create_app()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="GradientOS HTTP API server")
    parser.add_argument(
        "--host",
        default=os.environ.get("GRADIENT_API_HOST", "0.0.0.0"),
        help="Interface to bind the HTTP API (env: GRADIENT_API_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("GRADIENT_API_PORT", "4000")),
        help="Port for the HTTP API (env: GRADIENT_API_PORT)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable developer mode (uvicorn reload)",
    )
    args = parser.parse_args(argv)

    reload_env = os.environ.get("GRADIENT_API_RELOAD", "").lower()
    reload_enabled = args.dev or (reload_env in {"1", "true", "yes", "on"})

    import uvicorn

    uvicorn.run(
        "gradient_os.api.main:app",
        host=args.host,
        port=args.port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()


def _resolve_cors_origins() -> list[str]:
    raw = os.environ.get("GRADIENT_API_CORS", "")
    if not raw:
        return ["*"]
    origins = [item.strip() for item in raw.split(",")]
    return [origin for origin in origins if origin]
