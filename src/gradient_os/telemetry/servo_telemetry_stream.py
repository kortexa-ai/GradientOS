import argparse
import csv
import json
import socket
import time
from typing import Dict, List, Optional, Tuple

from ..arm_controller import servo_driver, servo_protocol, utils


# Default human-readable labels for alarm bits. These may vary by firmware.
LED_ALARM_LABELS: Dict[int, str] = {
    0: "Overload",
    1: "Overheat",
    2: "Overvoltage",
    3: "Undervoltage",
    4: "Stall",
    5: "Position Fault",
    6: "Comm/Error",
    7: "Unknown",
}
UNLOADING_LABELS: Dict[int, str] = {
    0: "Overload",
    1: "Overheat",
    2: "Overvoltage",
    3: "Undervoltage",
    4: "Stall",
    5: "Position Fault",
    6: "Comm/Error",
    7: "Unknown",
}


def _parse_ids(arg: Optional[str], include_gripper: bool) -> List[int]:
    """
    Parse a comma-separated list of servo IDs. If not provided, default to all configured IDs.
    Optionally exclude the gripper unless explicitly requested.
    """
    if arg:
        raw = [x.strip() for x in arg.split(",") if x.strip()]
        ids = []
        for tok in raw:
            try:
                ids.append(int(tok))
            except ValueError:
                pass
    else:
        ids = list(utils.SERVO_IDS)
    if not include_gripper:
        ids = [sid for sid in ids if sid != utils.SERVO_ID_GRIPPER]
    return ids


def _decode_block1(data: bytes) -> Tuple[int, int, int, float, int]:
    """
    Decode the 8-byte block starting at 0x38:
      - 0x38 (2) Current Position (signed)
      - 0x3A (2) Current Speed (signed)
      - 0x3C (2) Current Drive Duty (0..1000, unsigned)
      - 0x3E (1) Current Voltage (0.1V units)
      - 0x3F (1) Current Temperature (C)
    Returns: (pos_raw, speed_raw, drive_duty_pm, voltage_v_times10, temp_c)
    Where voltage is returned as float V.
    """
    pos = int.from_bytes(data[0:2], "little", signed=True)
    spd = int.from_bytes(data[2:4], "little", signed=True)
    duty = int.from_bytes(data[4:6], "little", signed=False)
    voltage_v = float(data[6]) / 10.0
    temp_c = int(data[7])
    return pos, spd, duty, voltage_v, temp_c


def _decode_block2(data: bytes) -> Tuple[int, int, float]:
    """
    Decode the 5-byte block starting at 0x41:
      - 0x41 (1) Status flags (HW error)
      - 0x42 (1) Moving status
      - 0x43 (1) reserved/unknown
      - 0x44 (1) reserved/unknown
      - 0x45 (2) Current (signed, 6.5 mA units) -> We read via the last two bytes
    Returns: (status, moving, current_a)
    """
    status = int(data[0])
    moving = int(data[1])
    # data[2], data[3] reserved/unknown per our table; keep but ignore
    current_raw = int.from_bytes(data[4:6], "little", signed=True)
    current_a = current_raw * 0.0065
    return status, moving, current_a


def _open_udp(target: Optional[str]) -> Optional[socket.socket]:
    if not target:
        return None
    host, port = target.rsplit(":", 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((host, int(port)))
    return sock


def main() -> None:
    ap = argparse.ArgumentParser(description="Stream and log Feetech STS3215 servo telemetry.")
    ap.add_argument("--ids", type=str, default=None, help="Comma-separated servo IDs. Default: all configured servos.")
    ap.add_argument("--include-gripper", action="store_true", help="Include the gripper servo (ID 100).")
    ap.add_argument("--fps", type=float, default=10.0, help="Sampling rate in Hz.")
    ap.add_argument("--out", type=str, default="servo_telemetry.csv", help="Output CSV path.")
    ap.add_argument("--duration", type=float, default=0.0, help="Optional duration in seconds. 0 = run until Ctrl-C.")
    ap.add_argument("--udp", type=str, default=None, help="Optional UDP target host:port to publish JSON frames.")
    ap.add_argument("--stdout", action="store_true", help="Also print a compact line to stdout per frame.")
    args = ap.parse_args()

    # Initialize servos and build ID set from present devices
    servo_driver.initialize_servos()
    requested_ids = _parse_ids(args.ids, include_gripper=bool(args.include_gripper))
    present = servo_protocol.get_present_servo_ids()
    servo_ids = [sid for sid in requested_ids if sid in present]
    if not servo_ids:
        print("[Pi Telemetry] No present servos match the requested IDs. Exiting.")
        return

    # Prepare CSV
    fieldnames = [
        "t",
        "id",
        "pos_raw",
        "speed_raw",
        "drive_duty_per_mille",
        "voltage_v",
        "temp_c",
        "status",
        "moving",
        "current_a",
        "unloading_condition",
        "led_alarm_condition",
        "unloading_hex",
        "unloading_bits",
        "led_alarm_hex",
        "led_alarm_bits",
        "unloading_names",
        "led_alarm_names",
    ]
    csv_file = open(args.out, "w", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    csv_file.flush()

    udp_sock = _open_udp(args.udp)
    period = 1.0 / max(1e-3, float(args.fps))
    t_end = time.time() + float(args.duration) if args.duration and args.duration > 0 else None

    print(f"[Pi Telemetry] Streaming {len(servo_ids)} servos at {args.fps:.2f} Hz")
    print(f"[Pi Telemetry] Writing CSV to: {args.out}")
    if udp_sock:
        print(f"[Pi Telemetry] UDP publishing to: {args.udp}")

    try:
        while True:
            t0 = time.time()
            if t_end is not None and t0 >= t_end:
                break

            # Block 1: 0x38..0x3F (8 bytes)
            blk1 = servo_protocol.sync_read_block(servo_ids, start_address=0x38, data_len=8, timeout_s=0.05)
            # Block 2: 0x41..0x45 (5 bytes)
            blk2 = servo_protocol.sync_read_block(servo_ids, start_address=0x41, data_len=5, timeout_s=0.05)
            # EEPROM alarms: 0x13..0x14 (2 bytes)
            blk3 = servo_protocol.sync_read_block(servo_ids, start_address=0x13, data_len=2, timeout_s=0.05)

            frame: Dict[int, dict] = {}
            for sid in servo_ids:
                d1 = blk1.get(sid)
                d2 = blk2.get(sid)
                d3 = blk3.get(sid)
                if not d1 and not d2 and not d3:
                    continue
                pos_raw = speed_raw = drive_duty = temp_c = None  # type: ignore[assignment]
                voltage_v = None  # type: ignore[assignment]
                status = moving = None  # type: ignore[assignment]
                current_a = None  # type: ignore[assignment]
                unloading_condition = None  # type: ignore[assignment]
                led_alarm_condition = None  # type: ignore[assignment]
                if d1 and len(d1) == 8:
                    pos_raw, speed_raw, drive_duty, voltage_v, temp_c = _decode_block1(d1)
                if d2 and len(d2) == 5:
                    status, moving, current_a = _decode_block2(d2)
                if d3 and len(d3) == 2:
                    unloading_condition = int(d3[0])
                    led_alarm_condition = int(d3[1])

                # Bitfield decoding helpers (list set bit indices)
                def _bits_set(b: Optional[int]) -> List[int]:
                    if b is None:
                        return []
                    return [i for i in range(8) if (b >> i) & 0x1]

                unloading_bits = _bits_set(unloading_condition)
                led_bits = _bits_set(led_alarm_condition)
                unloading_names = [UNLOADING_LABELS.get(i, f"b{i}") for i in unloading_bits]
                led_names = [LED_ALARM_LABELS.get(i, f"b{i}") for i in led_bits]

                row = {
                    "t": t0,
                    "id": sid,
                    "pos_raw": pos_raw,
                    "speed_raw": speed_raw,
                    "drive_duty_per_mille": drive_duty,
                    "voltage_v": voltage_v,
                    "temp_c": temp_c,
                    "status": status,
                    "moving": moving,
                    "current_a": current_a,
                    "unloading_condition": unloading_condition,
                    "led_alarm_condition": led_alarm_condition,
                    "unloading_hex": (f"0x{unloading_condition:02X}" if unloading_condition is not None else None),
                    "unloading_bits": ",".join(f"b{i}" for i in unloading_bits) if unloading_bits else "",
                    "led_alarm_hex": (f"0x{led_alarm_condition:02X}" if led_alarm_condition is not None else None),
                    "led_alarm_bits": ",".join(f"b{i}" for i in led_bits) if led_bits else "",
                    "unloading_names": "|".join(unloading_names) if unloading_names else "",
                    "led_alarm_names": "|".join(led_names) if led_names else "",
                }
                writer.writerow(row)
                frame[sid] = row

            csv_file.flush()

            if udp_sock and frame:
                try:
                    # For JSON, provide names as arrays for easier consumption
                    json_frame: Dict[int, dict] = {}
                    for sid, v in frame.items():
                        jd = dict(v)
                        if isinstance(jd.get("unloading_names"), str):
                            jd["unloading_names"] = [x for x in jd["unloading_names"].split("|") if x]
                        if isinstance(jd.get("led_alarm_names"), str):
                            jd["led_alarm_names"] = [x for x in jd["led_alarm_names"].split("|") if x]
                        json_frame[sid] = jd
                    msg = {"t": t0, "servos": json_frame}
                    udp_sock.send(json.dumps(msg).encode("utf-8"))
                except Exception:
                    pass

            if args.stdout and frame:
                try:
                    sample = {
                        sid: {
                            "V": v.get("voltage_v"),
                            "T": v.get("temp_c"),
                            "A": v.get("current_a"),
                            "duty": v.get("drive_duty_per_mille"),
                        }
                        for sid, v in frame.items()
                    }
                    print(f"[Pi Telemetry] {time.strftime('%H:%M:%S')} {sample}")
                except Exception:
                    pass

            dt = time.time() - t0
            if period - dt > 0:
                time.sleep(period - dt)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            csv_file.close()
        except Exception:
            pass
        if udp_sock:
            try:
                udp_sock.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()

