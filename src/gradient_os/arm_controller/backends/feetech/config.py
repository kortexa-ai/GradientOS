# backends/feetech/config.py
#
# Feetech STS/SCS series servo-specific configuration constants.
# These values are specific to the Feetech servo protocol and hardware.
#
# This module contains:
# - Protocol constants (headers, instruction codes, register addresses)
# - Communication parameters (baud rate, timeouts)
# - Default tuning values (PID gains, acceleration scaling)
#
# Robot-specific configuration (joint limits, servo IDs, etc.) should be
# defined elsewhere and passed to the FeetechBackend during initialization.

import math

# =============================================================================
# Serial Communication
# =============================================================================

# Default baud rate for Feetech servo communication
DEFAULT_BAUD_RATE = 1000000

# Default serial read timeout in seconds
SERIAL_READ_TIMEOUT = 0.05

# =============================================================================
# Feetech Protocol Constants
# =============================================================================

# Packet header bytes (all Feetech packets start with 0xFF 0xFF)
SERVO_HEADER = 0xFF

# Broadcast ID for sync commands (affects all servos on the bus)
SERVO_BROADCAST_ID = 0xFE

# -----------------------------------------------------------------------------
# Instruction Codes
# -----------------------------------------------------------------------------

SERVO_INSTRUCTION_PING = 0x01           # Check if servo is present
SERVO_INSTRUCTION_READ = 0x02           # Read from register(s)
SERVO_INSTRUCTION_WRITE = 0x03          # Write to register(s)
SERVO_INSTRUCTION_RESET = 0x06          # Factory reset (preserves ID)
SERVO_INSTRUCTION_RESTART = 0x08        # Reboot servo
SERVO_INSTRUCTION_CALIBRATE_MIDDLE = 0x0B  # Set current position as center
SERVO_INSTRUCTION_SYNC_READ = 0x82      # Read multiple servos at once
SERVO_INSTRUCTION_SYNC_WRITE = 0x83     # Write multiple servos at once

# -----------------------------------------------------------------------------
# Register Addresses - EEPROM Area (values persist after power cycle)
# -----------------------------------------------------------------------------

SERVO_ADDR_MIN_ANGLE_LIMIT = 0x09       # Minimum angle limit (2 bytes)
SERVO_ADDR_MAX_ANGLE_LIMIT = 0x0B       # Maximum angle limit (2 bytes)
SERVO_ADDR_POS_KP = 0x15                # Position PID - Proportional gain
SERVO_ADDR_POS_KD = 0x16                # Position PID - Derivative gain
SERVO_ADDR_POS_KI = 0x17                # Position PID - Integral gain
SERVO_ADDR_POSITION_CORRECTION = 0x1F  # Hardware zero offset (calibration)
SERVO_ADDR_WRITE_LOCK = 0x37            # EEPROM write lock (0=unlocked, 1=locked)

# -----------------------------------------------------------------------------
# Register Addresses - RAM Area (values reset on power cycle)
# -----------------------------------------------------------------------------

SERVO_ADDR_TARGET_ACCELERATION = 0x29   # Target acceleration (1 byte)
SERVO_ADDR_TARGET_POSITION = 0x2A       # Target position (2 bytes)
# Note: 0x2C-0x2D is "Goal Time", 0x2E-0x2F is "Goal Speed"
SERVO_ADDR_PRESENT_POSITION = 0x38      # Current position feedback (2 bytes)

# -----------------------------------------------------------------------------
# Sync Write Configuration
# -----------------------------------------------------------------------------

# Start address for Sync Write block (Accel, Pos, Time, Speed)
SYNC_WRITE_START_ADDRESS = SERVO_ADDR_TARGET_ACCELERATION  # 0x29

# Length of data block per servo in Sync Write:
# Accel (1) + Pos (2) + Time (2) + Speed (2) = 7 bytes
SYNC_WRITE_DATA_LEN_PER_SERVO = 7

# =============================================================================
# Motion Control Defaults
# =============================================================================

# Default servo speed if not specified (0-4095 scale)
DEFAULT_SERVO_SPEED = 500

# Default acceleration in deg/s² (converted to register value when written)
DEFAULT_SERVO_ACCELERATION_DEG_S2 = 500

# Scale factor for converting deg/s² to register value
# Register value = deg/s² / ACCELERATION_SCALE_FACTOR
# The servo register accepts 0-254, where 0 = max acceleration
ACCELERATION_SCALE_FACTOR = 100

# =============================================================================
# Default PID Gains
# =============================================================================

# These are reasonable starting values for Feetech STS3215 servos.
# Actual optimal values depend on mechanical load and desired response.

DEFAULT_KP = 50     # Proportional gain (0-254)
DEFAULT_KI = 1      # Integral gain (0-254)
DEFAULT_KD = 30     # Derivative gain (0-254)

# =============================================================================
# Servo Value Mapping
# =============================================================================

# Feetech servos use a 12-bit position value (0-4095)
# Center position is typically 2048
# Full range is typically ±π radians (±180°) around center

SERVO_VALUE_MIN = 0
SERVO_VALUE_MAX = 4095
SERVO_VALUE_CENTER = 2048

# Default angle range in radians (assuming ±π from center)
DEFAULT_ANGLE_RANGE_RAD = (-math.pi, math.pi)

# =============================================================================
# Telemetry Register Addresses
# =============================================================================

# Block 1: Position, Speed, Load/Duty, Voltage, Temperature (8 bytes @ 0x38)
TELEMETRY_BLOCK1_ADDRESS = 0x38
TELEMETRY_BLOCK1_LENGTH = 8

# Block 2: Status, Moving flag, reserved, reserved, Current (5 bytes @ 0x41)
TELEMETRY_BLOCK2_ADDRESS = 0x41
TELEMETRY_BLOCK2_LENGTH = 5

# Block 3: Unloading condition, LED alarm condition (2 bytes @ 0x13)
TELEMETRY_BLOCK3_ADDRESS = 0x13
TELEMETRY_BLOCK3_LENGTH = 2

# Current sensing scale factor: raw_value * CURRENT_SCALE_FACTOR = amps
CURRENT_SCALE_FACTOR = 0.0065

# Load bit mask: direction bit is bit 10 (0x400), magnitude is bits 0-9 (0x3FF)
LOAD_DIRECTION_BIT = 0x400
LOAD_MAGNITUDE_MASK = 0x3FF

# =============================================================================
# Error/Status Bit Masks (for response packets)
# =============================================================================

# Status bits in the error byte of response packets
STATUS_BIT_INPUT_VOLTAGE = 0x01   # Input voltage error
STATUS_BIT_ANGLE_LIMIT = 0x02     # Angle limit error  
STATUS_BIT_OVERHEATING = 0x04     # Overheating error
STATUS_BIT_RANGE = 0x08           # Range error
STATUS_BIT_CHECKSUM = 0x10        # Checksum error
STATUS_BIT_OVERLOAD = 0x20        # Overload error
STATUS_BIT_INSTRUCTION = 0x40     # Instruction error

# Human-readable names for status bits
STATUS_BIT_NAMES = {
    STATUS_BIT_INPUT_VOLTAGE: "Input Voltage",
    STATUS_BIT_ANGLE_LIMIT: "Angle Limit",
    STATUS_BIT_OVERHEATING: "Overheating",
    STATUS_BIT_RANGE: "Range",
    STATUS_BIT_CHECKSUM: "Checksum",
    STATUS_BIT_OVERLOAD: "Overload",
    STATUS_BIT_INSTRUCTION: "Instruction",
}


def names_for_status_bits(status_byte: int) -> list[str]:
    """
    Convert a status byte to a list of human-readable error names.
    
    Args:
        status_byte: The error/status byte from a servo response packet.
    
    Returns:
        list[str]: List of error names that are set in the status byte.
    """
    names = []
    for bit, name in STATUS_BIT_NAMES.items():
        if status_byte & bit:
            names.append(name)
    return names


# =============================================================================
# Telemetry Parsing
# =============================================================================

# Alarm/condition bit names (for unloading and LED alarm registers)
ALARM_BIT_NAMES = {
    0: "Overload",
    1: "Overheat",
    2: "Overvoltage",
    3: "Undervoltage",
    4: "Stall",
    5: "Position Fault",
    6: "Comm/Error",
    7: "Unknown",
}


def names_for_alarm_bits(alarm_byte: int) -> list[str]:
    """
    Convert an alarm byte to a list of human-readable alarm names.
    
    Args:
        alarm_byte: The alarm/condition byte from a servo.
    
    Returns:
        list[str]: List of alarm names that are set in the byte.
    """
    return [ALARM_BIT_NAMES.get(i, f"b{i}") for i in range(8) if ((alarm_byte >> i) & 1) == 1]


def bits_to_string(byte_val: int) -> str:
    """Convert a byte to a comma-separated string of set bit names."""
    bits = [f"b{i}" for i in range(8) if ((byte_val >> i) & 1) == 1]
    return ",".join(bits)


def parse_telemetry_block1(data: bytes) -> dict:
    """
    Parse telemetry block 1 (position, speed, load, voltage, temp).
    
    Args:
        data: 8-byte response from block 1 read
    
    Returns:
        dict: Parsed telemetry data with voltage_v, temp_c, drive_duty_per_mille
    """
    if len(data) != 8:
        return {}
    
    result = {}
    
    # Load/drive duty: direction in bit 10, magnitude in bits 0-9 (per-mille, 0-1023)
    load_raw = int.from_bytes(data[4:6], "little", signed=False)
    load_mag_pm = load_raw & LOAD_MAGNITUDE_MASK
    result["drive_duty_per_mille"] = load_mag_pm
    
    # Voltage: value / 10.0 = volts
    result["voltage_v"] = float(data[6]) / 10.0
    
    # Temperature: raw value in Celsius
    result["temp_c"] = int(data[7])
    
    return result


def parse_telemetry_block2(data: bytes) -> dict:
    """
    Parse telemetry block 2 (status, moving, current).
    
    Args:
        data: 5-byte response from block 2 read
    
    Returns:
        dict: Parsed telemetry data with status_byte, current_a
    """
    if len(data) != 5:
        return {}
    
    result = {}
    
    # Status byte
    status_byte = int(data[0])
    result["status_byte"] = status_byte
    result["status_bits"] = bits_to_string(status_byte)
    result["status_names"] = names_for_alarm_bits(status_byte)
    
    # Current: signed 16-bit, scale to amps
    current_raw = int.from_bytes(data[3:5], "little", signed=True)
    result["current_a"] = current_raw * CURRENT_SCALE_FACTOR
    
    return result


def parse_telemetry_block3(data: bytes) -> dict:
    """
    Parse telemetry block 3 (unloading condition, LED alarm).
    
    Args:
        data: 2-byte response from block 3 read
    
    Returns:
        dict: Parsed telemetry data with unloading/LED alarm info
    """
    if len(data) != 2:
        return {}
    
    result = {}
    
    unload = int(data[0])
    led = int(data[1])
    
    result["unloading_condition"] = unload
    result["led_alarm_condition"] = led
    result["unloading_bits"] = bits_to_string(unload)
    result["led_alarm_bits"] = bits_to_string(led)
    result["unloading_names"] = names_for_alarm_bits(unload)
    result["led_alarm_names"] = names_for_alarm_bits(led)
    
    return result

