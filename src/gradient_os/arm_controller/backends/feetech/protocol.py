# backends/feetech/protocol.py
#
# Low-level Feetech servo protocol implementation.
# Handles packet construction, checksum calculation, and serial communication
# for Feetech STS/SCS series servos.
#
# This module is designed to be independent of robot-specific configuration.
# It receives a serial port handle and servo IDs as parameters rather than
# using global state.

import time
import threading
from typing import Optional, Callable
import serial

from . import config

# =============================================================================
# Module State
# =============================================================================

# Global re-entrant lock to serialize all serial I/O across threads
_SERIAL_LOCK = threading.RLock()

# Telemetry buffer for Sync Read profiling (write, read, parse durations in seconds)
_sync_profiles: list[tuple[float, float, float]] = []

# Cache of detected servo IDs (populated by ping operations)
_present_servo_ids: set[int] = set()


def get_present_servo_ids() -> set[int]:
    """
    Returns the set of servo IDs that responded to ping commands.
    
    Returns:
        set[int]: Set of detected servo IDs.
    """
    return _present_servo_ids.copy()


def clear_present_servo_ids() -> None:
    """Clear the cache of detected servo IDs."""
    global _present_servo_ids
    _present_servo_ids = set()


def add_present_servo_id(servo_id: int) -> None:
    """Add a servo ID to the detected set."""
    _present_servo_ids.add(servo_id)


def get_sync_profiles() -> list[tuple[float, float, float]]:
    """
    Return and clear the collected Sync-Read timing tuples.
    
    Returns:
        list[tuple[float, float, float]]: List of (write_dur, read_dur, parse_dur) in seconds.
    """
    global _sync_profiles
    out = _sync_profiles[:]
    _sync_profiles.clear()
    return out


# =============================================================================
# Checksum Calculation
# =============================================================================

def calculate_checksum(packet_data: bytearray) -> int:
    """
    Calculates the Feetech checksum for a packet.
    
    The checksum is the bitwise inverse of the sum of all bytes in the packet
    (excluding the initial 0xFF headers).
    
    Args:
        packet_data: The packet data (from Servo ID to last parameter) to sum.
    
    Returns:
        int: The calculated checksum byte (0-255).
    """
    current_sum = sum(packet_data)
    return (~current_sum) & 0xFF


# =============================================================================
# Basic Communication Functions
# =============================================================================

def ping(ser: serial.Serial, servo_id: int) -> bool:
    """
    Send a PING instruction to check if a servo is present.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the servo to ping.
    
    Returns:
        bool: True if a valid status packet is received, False otherwise.
    """
    if ser is None or not ser.is_open:
        return False

    # PING Packet: [0xFF, 0xFF, ID, Length=2, Instr=0x01, Checksum]
    ping_command = bytearray(6)
    ping_command[0] = config.SERVO_HEADER
    ping_command[1] = config.SERVO_HEADER
    ping_command[2] = servo_id
    ping_command[3] = 2  # Length = NumParams(0) + 2
    ping_command[4] = config.SERVO_INSTRUCTION_PING
    ping_command[5] = calculate_checksum(ping_command[2:5])

    try:
        with _SERIAL_LOCK:
            ser.reset_input_buffer()
            ser.write(ping_command)
            # Expected response: [0xFF, 0xFF, ID, Length=2, Error=0, Checksum]
            response = ser.read(6)

        if len(response) == 6 and response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id:
            _present_servo_ids.add(servo_id)
            return True
        return False

    except Exception as e:
        print(f"[Feetech PING] Error during ping for servo {servo_id}: {e}")
        return False


def read_register_byte(ser: serial.Serial, servo_id: int, register_address: int) -> Optional[int]:
    """
    Read a single byte from a servo register.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
        register_address: The address of the register to read.
    
    Returns:
        Optional[int]: The byte value (0-255), or None on failure.
    """
    if ser is None or not ser.is_open:
        return None

    # Command: [0xFF, 0xFF, ID, Length=4, Instr=0x02, Addr, BytesToRead=1, Checksum]
    read_command = bytearray(8)
    read_command[0] = config.SERVO_HEADER
    read_command[1] = config.SERVO_HEADER
    read_command[2] = servo_id
    read_command[3] = 4  # Length
    read_command[4] = config.SERVO_INSTRUCTION_READ
    read_command[5] = register_address
    read_command[6] = 1  # Number of bytes to read
    read_command[7] = calculate_checksum(read_command[2:7])

    try:
        with _SERIAL_LOCK:
            ser.reset_input_buffer()
            ser.write(read_command)
            # Expected response: [0xFF, 0xFF, ID, Length=3, Error, Value, Checksum]
            response = ser.read(7)

        if len(response) < 7:
            return None
        if not (response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id):
            return None
        if response[6] != calculate_checksum(response[2:6]):
            return None
        if response[4] != 0:  # Error byte
            return None
        return response[5]

    except Exception:
        return None


def read_register_word(ser: serial.Serial, servo_id: int, register_address: int) -> Optional[int]:
    """
    Read a 16-bit word (2 bytes) from a servo register.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
        register_address: The starting address of the register to read.
    
    Returns:
        Optional[int]: The 16-bit value, or None on failure.
    """
    if ser is None or not ser.is_open:
        return None

    # Command: [0xFF, 0xFF, ID, Length=4, Instr=0x02, Addr, BytesToRead=2, Checksum]
    read_command = bytearray(8)
    read_command[0] = config.SERVO_HEADER
    read_command[1] = config.SERVO_HEADER
    read_command[2] = servo_id
    read_command[3] = 4  # Length
    read_command[4] = config.SERVO_INSTRUCTION_READ
    read_command[5] = register_address
    read_command[6] = 2  # Number of bytes to read
    read_command[7] = calculate_checksum(read_command[2:7])

    try:
        with _SERIAL_LOCK:
            ser.reset_input_buffer()
            ser.write(read_command)
            # Expected response: [0xFF, 0xFF, ID, Length=4, Error, Val_L, Val_H, Checksum]
            response = ser.read(8)

        if len(response) < 8:
            return None
        if not (response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id):
            return None
        if response[7] != calculate_checksum(response[2:7]):
            return None
        if response[4] != 0:  # Error byte
            return None
        
        # Little-endian 16-bit value
        value = response[5] | (response[6] << 8)
        return value

    except Exception:
        return None


def write_register_byte(ser: serial.Serial, servo_id: int, register_address: int, value: int) -> bool:
    """
    Write a single byte to a servo register.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
        register_address: The address of the register to write.
        value: The byte value to write (0-255).
    
    Returns:
        bool: True on success, False on failure.
    """
    if ser is None or not ser.is_open:
        return False

    val_clamped = int(max(0, min(255, value)))

    # Packet: [0xFF, 0xFF, ID, Length=4, Instr=0x03, Addr, Value, Checksum]
    packet = bytearray(8)
    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = servo_id
    packet[3] = 4  # Length = Instr(1) + Addr(1) + Value(1) + 1
    packet[4] = config.SERVO_INSTRUCTION_WRITE
    packet[5] = register_address
    packet[6] = val_clamped
    packet[7] = calculate_checksum(packet[2:7])

    try:
        with _SERIAL_LOCK:
            ser.write(packet)
        return True
    except Exception as e:
        print(f"[Feetech] Error writing byte to servo {servo_id} register {hex(register_address)}: {e}")
        return False


def write_register_word(ser: serial.Serial, servo_id: int, register_address: int, value: int) -> bool:
    """
    Write a 16-bit word to a servo register.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
        register_address: The address of the register to write.
        value: The 16-bit value to write.
    
    Returns:
        bool: True on success, False on failure.
    """
    if ser is None or not ser.is_open:
        return False

    val_clamped = int(value)

    # Packet: [0xFF, 0xFF, ID, Length=5, Instr=0x03, Addr, Val_L, Val_H, Checksum]
    packet = bytearray(9)
    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = servo_id
    packet[3] = 5  # Length
    packet[4] = config.SERVO_INSTRUCTION_WRITE
    packet[5] = register_address
    packet[6] = val_clamped & 0xFF         # Low byte
    packet[7] = (val_clamped >> 8) & 0xFF  # High byte
    packet[8] = calculate_checksum(packet[2:8])

    try:
        with _SERIAL_LOCK:
            ser.write(packet)
        return True
    except Exception as e:
        print(f"[Feetech] Error writing word to servo {servo_id} register {hex(register_address)}: {e}")
        return False


# =============================================================================
# Position Reading
# =============================================================================

def read_position(
    ser: serial.Serial,
    servo_id: int,
    alert_callback: Optional[Callable] = None,
) -> Optional[int]:
    """
    Read the current position of a single servo.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
        alert_callback: Optional callback for reporting errors.
    
    Returns:
        Optional[int]: The servo's current raw position (0-4095), or None on failure.
    """
    if ser is None or not ser.is_open:
        return None

    # Command: [0xFF, 0xFF, ID, Length=4, Instr=0x02, Addr=0x38, BytesToRead=2, Checksum]
    read_command = bytearray(8)
    read_command[0] = config.SERVO_HEADER
    read_command[1] = config.SERVO_HEADER
    read_command[2] = servo_id
    read_command[3] = 4
    read_command[4] = config.SERVO_INSTRUCTION_READ
    read_command[5] = config.SERVO_ADDR_PRESENT_POSITION
    read_command[6] = 2
    read_command[7] = calculate_checksum(read_command[2:7])

    try:
        with _SERIAL_LOCK:
            ser.reset_input_buffer()
            ser.write(read_command)
            response = ser.read(8)

        if not response or len(response) < 8:
            return None
        if response[0] != config.SERVO_HEADER or response[1] != config.SERVO_HEADER:
            return None
        if response[2] != servo_id:
            return None
        if response[3] != 4:  # Length field should be 4
            return None
        
        expected_checksum = calculate_checksum(response[2:7])
        if expected_checksum != response[7]:
            return None

        error_byte = response[4]
        if error_byte != 0:
            if alert_callback:
                names = config.names_for_status_bits(error_byte)
                alert_callback(servo_id, error_byte, names)
            return None

        # Position is a signed 16-bit value (for multi-turn mode compatibility)
        position = int.from_bytes(response[5:7], byteorder='little', signed=True)
        return position

    except Exception as e:
        print(f"[Feetech ReadPos] Servo {servo_id}: Error: {e}")
        return None


# =============================================================================
# Sync Write (Batch Position/Speed/Accel)
# =============================================================================

def sync_write_goal_pos_speed_accel(ser: serial.Serial, servo_data_list: list[tuple[int, int, int, int]]) -> None:
    """
    Send a SYNC WRITE packet to command multiple servos simultaneously.
    
    This is the most efficient way to command multiple servos as it bundles
    all commands into a single serial transmission.
    
    Args:
        ser: Open serial port handle.
        servo_data_list: List of tuples, each containing:
                         (servo_id, position_value, speed_value, accel_register_value)
                         - servo_id: Hardware ID of the servo
                         - position_value: Target position (0-4095)
                         - speed_value: Target speed (0-4095)
                         - accel_register_value: Acceleration (0-254, 0=max)
    """
    if ser is None or not ser.is_open:
        return

    num_servos = len(servo_data_list)
    if num_servos == 0:
        return

    # Calculate packet length
    # PacketLen = num_servos * (ID + DataLen) + 4
    packet_len_field = num_servos * (1 + config.SYNC_WRITE_DATA_LEN_PER_SERVO) + 4

    # Total packet: Header(2) + BroadcastID(1) + Len(1) + Content + Checksum(1)
    total_packet_bytes = 4 + packet_len_field + 1
    packet = bytearray(total_packet_bytes)

    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = config.SERVO_BROADCAST_ID
    packet[3] = packet_len_field
    packet[4] = config.SERVO_INSTRUCTION_SYNC_WRITE
    packet[5] = config.SYNC_WRITE_START_ADDRESS
    packet[6] = config.SYNC_WRITE_DATA_LEN_PER_SERVO

    idx = 7
    for servo_id, pos_val, speed_val, accel_reg_val in servo_data_list:
        packet[idx] = servo_id
        idx += 1
        
        # Data order: Accel(1), Pos_L(1), Pos_H(1), Time_L(1), Time_H(1), Spd_L(1), Spd_H(1)
        packet[idx] = accel_reg_val
        idx += 1
        packet[idx] = pos_val & 0xFF
        idx += 1
        packet[idx] = (pos_val >> 8) & 0xFF
        idx += 1
        packet[idx] = 0  # Time_L (always 0)
        idx += 1
        packet[idx] = 0  # Time_H (always 0)
        idx += 1
        packet[idx] = speed_val & 0xFF
        idx += 1
        packet[idx] = (speed_val >> 8) & 0xFF
        idx += 1

    # Calculate checksum (from Broadcast_ID to last data byte)
    packet[idx] = calculate_checksum(packet[2:idx])

    try:
        with _SERIAL_LOCK:
            ser.write(packet[:idx + 1])
    except Exception as e:
        print(f"[Feetech SyncWrite] Error: {e}")


# =============================================================================
# Sync Read (Batch Position Reading)
# =============================================================================

def sync_read_positions(
    ser: serial.Serial,
    servo_ids: list[int],
    timeout_s: Optional[float] = None,
    poll_delay_s: float = 0.0,
    diagnostics: bool = True,
    alert_callback: Optional[Callable] = None,
) -> dict[int, int]:
    """
    Read positions from multiple servos using a single SYNC READ command.
    
    This is significantly faster than reading one by one, enabling high-frequency
    feedback for closed-loop control.
    
    Args:
        ser: Open serial port handle.
        servo_ids: List of servo IDs to read from.
        timeout_s: Optional per-call serial read timeout override.
        poll_delay_s: Optional delay after command before reading response.
        diagnostics: Whether to collect timing data.
        alert_callback: Optional callback for reporting errors.
    
    Returns:
        dict[int, int]: Mapping of servo_id to raw position. May be partial
                       if some servos did not respond.
    """
    if ser is None or not ser.is_open:
        return {}

    num_servos = len(servo_ids)
    if num_servos == 0:
        return {}

    # Construct Sync Read packet
    # [0xFF, 0xFF, Broadcast_ID, Len, Instr, StartAddr, DataLen, ID1, ID2, ..., Checksum]
    packet_len_field = num_servos + 4
    packet = bytearray(7 + num_servos + 1)
    
    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = config.SERVO_BROADCAST_ID
    packet[3] = packet_len_field
    packet[4] = config.SERVO_INSTRUCTION_SYNC_READ
    packet[5] = config.SERVO_ADDR_PRESENT_POSITION
    packet[6] = 2  # Read 2 bytes (position)

    for i, servo_id in enumerate(servo_ids):
        packet[7 + i] = servo_id

    packet[-1] = calculate_checksum(packet[2:-1])

    try:
        # Optionally override timeout
        original_timeout = None
        if timeout_s is not None:
            original_timeout = ser.timeout
            ser.timeout = timeout_s

        # WRITE
        write_start = time.perf_counter()
        with _SERIAL_LOCK:
            ser.reset_input_buffer()
            ser.write(packet)
        write_dur = time.perf_counter() - write_start

        if poll_delay_s > 0.0:
            time.sleep(poll_delay_s)

        # READ
        bytes_to_read = num_servos * 8  # Each servo sends 8-byte status packet
        read_start = time.perf_counter()
        with _SERIAL_LOCK:
            response_data = ser.read(bytes_to_read)
        read_dur = time.perf_counter() - read_start

        if len(response_data) < bytes_to_read:
            print(f"[Feetech SyncRead] WARNING: Expected {bytes_to_read} bytes, got {len(response_data)}.")

        # PARSE
        positions = {}
        expected_ids = set(servo_ids)
        parse_start = time.perf_counter()

        for i in range(0, len(response_data) - 7):
            if response_data[i] == config.SERVO_HEADER and response_data[i+1] == config.SERVO_HEADER:
                pkt = response_data[i : i+8]
                response_id = pkt[2]
                
                if response_id not in expected_ids:
                    continue

                # Check error byte
                if pkt[4] != 0:
                    if alert_callback:
                        names = config.names_for_status_bits(pkt[4])
                        alert_callback(response_id, pkt[4], names)
                    continue

                # Validate checksum
                if calculate_checksum(pkt[2:7]) != pkt[7]:
                    continue

                # Extract position (signed 16-bit, little-endian)
                position = int.from_bytes(pkt[5:7], byteorder='little', signed=True)
                positions[response_id] = position
                expected_ids.discard(response_id)

        parse_dur = time.perf_counter() - parse_start

        if diagnostics:
            _sync_profiles.append((write_dur, read_dur, parse_dur))

        if expected_ids:
            missing = list(expected_ids)
            print(f"[Feetech SyncRead] No response from IDs: {missing}")
            if alert_callback:
                for sid in missing:
                    alert_callback(sid, -1, ["Timeout"])

        return positions

    except Exception as e:
        print(f"[Feetech SyncRead] Error: {e}")
        return {}
    finally:
        if timeout_s is not None and original_timeout is not None:
            ser.timeout = original_timeout


# =============================================================================
# Sync Read (Generic Block)
# =============================================================================
def sync_read_block(
    ser: serial.Serial,
    servo_ids: list[int],
    start_address: int,
    data_len: int,
    timeout_s: Optional[float] = None,
    poll_delay_s: float = 0.0,
    diagnostics: bool = False,
) -> dict[int, bytes]:
    """
    Perform a generic SYNC READ for a contiguous block of registers starting at
    `start_address` with length `data_len` for each servo in `servo_ids`.
    
    Returns a mapping of servo_id -> raw bytes (length == data_len) for all servos
    that responded with a valid status packet. Missing IDs indicate no valid
    response was parsed.
    """
    if ser is None or not ser.is_open:
        return {}

    num_servos = len(servo_ids)
    if num_servos == 0 or data_len <= 0:
        return {}

    packet_len_field = num_servos + 4
    packet = bytearray(7 + num_servos + 1)
    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = config.SERVO_BROADCAST_ID
    packet[3] = packet_len_field
    packet[4] = config.SERVO_INSTRUCTION_SYNC_READ
    packet[5] = start_address
    packet[6] = data_len
    for i, servo_id in enumerate(servo_ids):
        packet[7 + i] = servo_id
    packet[-1] = calculate_checksum(packet[2:-1])

    try:
        original_timeout = None
        if timeout_s is not None:
            original_timeout = ser.timeout
            ser.timeout = timeout_s

        write_start = time.perf_counter()
        with _SERIAL_LOCK:
            ser.reset_input_buffer()
            ser.write(packet)
        write_dur = time.perf_counter() - write_start

        if poll_delay_s > 0.0:
            time.sleep(poll_delay_s)

        per_packet = 6 + data_len
        bytes_to_read = num_servos * per_packet
        read_start = time.perf_counter()
        with _SERIAL_LOCK:
            response_data = ser.read(bytes_to_read)
        read_dur = time.perf_counter() - read_start

        if len(response_data) < per_packet:
            return {}

        results: dict[int, bytes] = {}
        expected_ids = set(servo_ids)
        parse_start = time.perf_counter()
        i = 0
        end = len(response_data) - per_packet + 1
        while i < end:
            if response_data[i] == config.SERVO_HEADER and response_data[i + 1] == config.SERVO_HEADER:
                pkt = response_data[i : i + per_packet]
                sid = pkt[2]
                if sid in expected_ids:
                    if pkt[4] == 0:
                        if calculate_checksum(pkt[2:(2 + 1 + 1 + 1 + data_len)]) == pkt[-1]:
                            results[sid] = bytes(pkt[5 : 5 + data_len])
                            expected_ids.discard(sid)
                            i += per_packet
                            continue
                i += 1
            else:
                i += 1
        parse_dur = time.perf_counter() - parse_start

        if diagnostics:
            _sync_profiles.append((write_dur, read_dur, parse_dur))

        return results
    except Exception as e:
        print(f"[Feetech SyncReadBlk] Error: {e}")
        return {}
    finally:
        if timeout_s is not None and original_timeout is not None:
            ser.timeout = original_timeout


# =============================================================================
# Special Commands
# =============================================================================

def calibrate_middle_position(ser: serial.Serial, servo_id: int) -> bool:
    """
    Send the Calibrate Middle Position command (0x0B).
    
    This instructs the servo to treat its current physical position as the
    center point (raw value 2048).
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
    
    Returns:
        bool: True on success, False on failure.
    """
    if ser is None or not ser.is_open:
        return False

    # Packet: [0xFF, 0xFF, ID, Length=2, Instr=0x0B, Checksum]
    packet = bytearray(6)
    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = servo_id
    packet[3] = 2
    packet[4] = config.SERVO_INSTRUCTION_CALIBRATE_MIDDLE
    packet[5] = calculate_checksum(packet[2:5])

    try:
        with _SERIAL_LOCK:
            ser.write(packet)
        return True
    except Exception as e:
        print(f"[Feetech] Error sending calibrate command to servo {servo_id}: {e}")
        return False


def factory_reset(ser: serial.Serial, servo_id: int) -> bool:
    """
    Send the Factory Reset command (0x06).
    
    This resets all EEPROM values to factory defaults EXCEPT the servo ID.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
    
    Returns:
        bool: True on success, False on failure.
    """
    if ser is None or not ser.is_open:
        return False

    packet = bytearray(6)
    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = servo_id
    packet[3] = 2
    packet[4] = config.SERVO_INSTRUCTION_RESET
    packet[5] = calculate_checksum(packet[2:5])

    try:
        with _SERIAL_LOCK:
            ser.write(packet)
        return True
    except Exception as e:
        print(f"[Feetech] Error sending factory reset to servo {servo_id}: {e}")
        return False


def restart(ser: serial.Serial, servo_id: int) -> bool:
    """
    Send the Restart command (0x08).
    
    This is equivalent to a power cycle of the servo.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
    
    Returns:
        bool: True on success, False on failure.
    """
    if ser is None or not ser.is_open:
        return False

    packet = bytearray(6)
    packet[0] = config.SERVO_HEADER
    packet[1] = config.SERVO_HEADER
    packet[2] = servo_id
    packet[3] = 2
    packet[4] = config.SERVO_INSTRUCTION_RESTART
    packet[5] = calculate_checksum(packet[2:5])

    try:
        with _SERIAL_LOCK:
            ser.write(packet)
        return True
    except Exception as e:
        print(f"[Feetech] Error sending restart to servo {servo_id}: {e}")
        return False


def write_angle_limits(
    ser: serial.Serial,
    servo_id: int,
    min_limit_raw: int,
    max_limit_raw: int,
) -> bool:
    """
    Write minimum and maximum angle limits to a servo's EEPROM.
    
    This requires unlocking the EEPROM, writing values, and re-locking.
    
    Args:
        ser: Open serial port handle.
        servo_id: The hardware ID of the target servo.
        min_limit_raw: Raw minimum angle limit (0-4095).
        max_limit_raw: Raw maximum angle limit (0-4095).
    
    Returns:
        bool: True if all steps were successful, False otherwise.
    """
    # 1. Unlock EEPROM
    if not write_register_byte(ser, servo_id, config.SERVO_ADDR_WRITE_LOCK, 0):
        print(f"[Feetech] Failed to unlock EEPROM for servo {servo_id}")
        return False
    time.sleep(0.01)

    # 2. Write limits
    min_ok = write_register_word(ser, servo_id, config.SERVO_ADDR_MIN_ANGLE_LIMIT, min_limit_raw)
    time.sleep(0.01)
    max_ok = write_register_word(ser, servo_id, config.SERVO_ADDR_MAX_ANGLE_LIMIT, max_limit_raw)
    time.sleep(0.01)

    if not (min_ok and max_ok):
        # Try to re-lock even on failure
        write_register_byte(ser, servo_id, config.SERVO_ADDR_WRITE_LOCK, 1)
        return False

    # 3. Re-lock EEPROM
    write_register_byte(ser, servo_id, config.SERVO_ADDR_WRITE_LOCK, 1)
    return True

