# actuator_interface.py
# 
# Abstract base class defining the interface that any actuator backend must implement.
# This allows GradientOS to work with different servo types (Feetech, Dynamixel, etc.)
# or even different actuator systems (steppers, hydraulics) by implementing this interface.
#
# The interface is designed around the concept of "logical joints" - the kinematic joints
# of the robot - rather than physical servos. This abstraction allows the backend to
# handle the mapping from logical joints to physical actuators (e.g., twin-motor joints,
# gear ratios, etc.) internally.

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
import math
import numpy as np

if TYPE_CHECKING:
    from .robots.base import RobotConfig


class ActuatorBackend(ABC):
    """
    Abstract base class defining the interface for actuator control systems.
    
    Any actuator backend (Feetech servos, Dynamixel servos, stepper motors, etc.)
    must implement this interface to be compatible with GradientOS's motion planning
    and trajectory execution systems.
    
    The interface operates on "logical joints" which represent the kinematic joints
    of the robot. The backend is responsible for mapping these to physical actuators.
    
    Key Concepts:
    -------------
    - Logical Joint: A joint in the kinematic model (e.g., shoulder, elbow)
    - Physical Actuator: The actual hardware (servo, motor) that moves the joint
    - A single logical joint may be driven by multiple physical actuators (e.g., twin motors)
    
    Thread Safety:
    --------------
    Implementations should be thread-safe, as methods may be called from multiple threads
    (e.g., the main control loop and a trajectory executor thread).
    """
    
    # =========================================================================
    # Initialization & Configuration
    # =========================================================================
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the actuator system (open serial ports, ping devices, etc.).
        
        This method should:
        - Establish communication with the hardware
        - Detect which actuators are present
        - Apply default configuration (PID gains, limits, etc.)
        - Populate internal state about the system
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """
        Cleanly shut down the actuator system.
        
        This method should:
        - Stop any ongoing motion
        - Close serial ports/connections
        - Release any resources
        """
        pass
    
    @property
    @abstractmethod
    def num_joints(self) -> int:
        """
        Returns the number of logical joints this backend controls.
        
        Returns:
            int: Number of controllable joints in the kinematic model.
        """
        pass
    
    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """
        Check if the backend has been successfully initialized.
        
        Returns:
            bool: True if initialize() has been called successfully.
        """
        pass
    
    @property
    @abstractmethod
    def encoder_resolution(self) -> int:
        """
        Returns the encoder resolution (maximum raw value) for this actuator type.
        
        For example:
        - Feetech STS3215 servos: 4095 (12-bit encoder)
        - Dynamixel servos: may vary by model (typically 4095 or 65535)
        - Stepper motors: depends on microstepping configuration
        
        This value is used for converting between angles and raw encoder values.
        
        Returns:
            int: Maximum raw encoder value (e.g., 4095 for 12-bit encoders)
        """
        pass
    
    @property
    def encoder_center(self) -> int:
        """
        Returns the center encoder value (representing 0 radians).
        
        Default implementation returns encoder_resolution // 2 (e.g., 2048 for 4095).
        Override if your actuator uses a different center value.
        
        Returns:
            int: Center encoder value
        """
        return self.encoder_resolution // 2
    
    # =========================================================================
    # Position Control - Standard Interface
    # =========================================================================
    
    @abstractmethod
    def set_joint_positions(
        self,
        positions_rad: list[float],
        speed: float,
        acceleration: float,
    ) -> None:
        """
        Command all joints to move to specified positions.
        
        This is the primary method for commanding joint motion. The backend is
        responsible for translating these logical joint angles into the appropriate
        commands for the physical actuators.
        
        Args:
            positions_rad: List of target positions in radians, one per logical joint.
                           Length must equal `num_joints`.
            speed: Movement speed. Units are backend-specific but typically:
                   - For servos: 0-4095 (servo register value) or deg/s
                   - For steppers: steps/second
            acceleration: Movement acceleration. Units are backend-specific but typically:
                          - For servos: deg/s² or register value
                          - For steppers: steps/s²
        
        Raises:
            ValueError: If len(positions_rad) != num_joints
        """
        pass
    
    @abstractmethod
    def get_joint_positions(self, verbose: bool = False) -> list[float]:
        """
        Read the current position of all logical joints.
        
        Args:
            verbose: If True, print debug information about the read operation.
        
        Returns:
            list[float]: Current joint positions in radians, one per logical joint.
                         Length equals `num_joints`.
        """
        pass
    
    # =========================================================================
    # High-Speed Batch Operations (for real-time control loops)
    # =========================================================================
    
    @abstractmethod
    def prepare_sync_write_commands(
        self,
        positions_rad: list[float],
        speed: int = 4095,
        accel: int = 0,
    ) -> list[tuple]:
        """
        Pre-compute the low-level commands for a sync write operation.
        
        This method converts logical joint positions to the format required by the
        hardware, allowing the actual write to be performed with minimal latency
        in a real-time control loop.
        
        Args:
            positions_rad: Target joint positions in radians.
            speed: Speed value (backend-specific, typically 0-4095 for servos).
            accel: Acceleration value (backend-specific, typically 0-254 for servos).
        
        Returns:
            list[tuple]: Backend-specific command data ready for sync_write().
        """
        pass
    
    @abstractmethod
    def sync_write(self, commands: list[tuple]) -> None:
        """
        Execute a batch write operation with pre-computed commands.
        
        This is the fastest way to command multiple actuators simultaneously.
        The commands should be prepared using prepare_sync_write_commands().
        
        Args:
            commands: Pre-computed command data from prepare_sync_write_commands().
        """
        pass
    
    @abstractmethod
    def sync_read_positions(
        self,
        timeout_s: Optional[float] = None,
    ) -> dict[int, int]:
        """
        Read positions from all actuators in a single batch operation.
        
        This is the fastest way to get feedback from multiple actuators for
        closed-loop control.
        
        Args:
            timeout_s: Optional timeout for the read operation in seconds.
        
        Returns:
            dict[int, int]: Mapping of actuator ID to raw position value.
                           The backend is responsible for providing a method
                           to convert these to joint angles if needed.
        """
        pass
    
    @abstractmethod
    def raw_to_joint_positions(self, raw_positions: dict[int, int]) -> list[float]:
        """
        Convert raw actuator position readings to logical joint angles.
        
        Args:
            raw_positions: Mapping of actuator ID to raw position value
                          (as returned by sync_read_positions).
        
        Returns:
            list[float]: Joint positions in radians, one per logical joint.
        """
        pass
    
    # =========================================================================
    # Single Actuator Control (for gripper, calibration, etc.)
    # =========================================================================
    
    @abstractmethod
    def set_single_actuator_position(
        self,
        actuator_id: int,
        position_rad: float,
        speed: int,
        accel: int,
    ) -> None:
        """
        Command a single actuator to a specific position.
        
        Used for controlling auxiliary actuators (gripper) or for calibration.
        
        Args:
            actuator_id: The hardware ID of the actuator.
            position_rad: Target position in radians.
            speed: Movement speed (backend-specific units).
            accel: Movement acceleration (backend-specific units).
        """
        pass
    
    @abstractmethod
    def read_single_actuator_position(self, actuator_id: int) -> Optional[int]:
        """
        Read the raw position of a single actuator.
        
        Args:
            actuator_id: The hardware ID of the actuator.
        
        Returns:
            Optional[int]: Raw position value, or None if read failed.
        """
        pass
    
    # =========================================================================
    # Calibration & Configuration
    # =========================================================================
    
    @abstractmethod
    def set_current_position_as_zero(self, actuator_id: int) -> bool:
        """
        Set the current physical position of an actuator as its zero point.
        
        This is used for calibration - the actuator will treat its current
        position as the origin (typically raw value 2048 for servos).
        
        Args:
            actuator_id: The hardware ID of the actuator to calibrate.
        
        Returns:
            bool: True if calibration was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def set_pid_gains(
        self,
        actuator_id: int,
        kp: int,
        ki: int,
        kd: int,
    ) -> bool:
        """
        Set the PID gains for a specific actuator's internal controller.
        
        Args:
            actuator_id: The hardware ID of the actuator.
            kp: Proportional gain.
            ki: Integral gain.
            kd: Derivative gain.
        
        Returns:
            bool: True if gains were set successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def apply_joint_limits(self) -> bool:
        """
        Apply the configured joint limits to all actuators.
        
        This writes the limit values to the actuators' EEPROM so they
        enforce the limits at the hardware level.
        
        Returns:
            bool: True if all limits were set successfully, False otherwise.
        """
        pass
    
    # =========================================================================
    # Gripper Support (Optional - default implementations provided)
    # =========================================================================
    
    @property
    def has_gripper(self) -> bool:
        """
        Check if this backend has a gripper attached.
        
        Returns:
            bool: True if a gripper is present and controllable.
        """
        return False
    
    @property
    def gripper_actuator_id(self) -> Optional[int]:
        """
        Get the hardware ID of the gripper actuator.
        
        Returns:
            Optional[int]: Gripper actuator ID, or None if no gripper.
        """
        return None
    
    def set_gripper_position(self, position_rad: float, speed: int = 50, accel: int = 0) -> None:
        """
        Set the gripper to a specific position.
        
        Args:
            position_rad: Target gripper position in radians.
            speed: Movement speed.
            accel: Movement acceleration.
        """
        if self.has_gripper and self.gripper_actuator_id is not None:
            self.set_single_actuator_position(
                self.gripper_actuator_id, position_rad, speed, accel
            )
    
    def get_gripper_position(self) -> Optional[float]:
        """
        Read the current gripper position.
        
        Returns:
            Optional[float]: Gripper position in radians, or None if not available.
        """
        return None
    
    # =========================================================================
    # Diagnostics & Utilities
    # =========================================================================
    
    @abstractmethod
    def get_present_actuator_ids(self) -> set[int]:
        """
        Get the set of actuator IDs that were detected during initialization.
        
        Returns:
            set[int]: Set of hardware IDs for actuators that responded to ping.
        """
        pass
    
    @abstractmethod
    def ping_actuator(self, actuator_id: int) -> bool:
        """
        Check if a specific actuator is responsive.
        
        Args:
            actuator_id: The hardware ID to ping.
        
        Returns:
            bool: True if the actuator responded, False otherwise.
        """
        pass
    
    def factory_reset_actuator(self, actuator_id: int) -> bool:
        """
        Reset an actuator to factory defaults.
        
        Args:
            actuator_id: The hardware ID of the actuator to reset.
        
        Returns:
            bool: True if reset was successful, False otherwise.
        """
        return False  # Default: not supported
    
    def restart_actuator(self, actuator_id: int) -> bool:
        """
        Restart/reboot an actuator.
        
        Args:
            actuator_id: The hardware ID of the actuator to restart.
        
        Returns:
            bool: True if restart command was sent successfully.
        """
        return False  # Default: not supported


class SimulationBackend(ActuatorBackend):
    """
    A simulation backend that maintains joint positions in memory without hardware.
    
    This is useful for testing motion planning and trajectory execution without
    physical hardware connected.
    """
    
    def __init__(
        self,
        robot_config: Optional['RobotConfig'] = None,
        num_joints: Optional[int] = None,
        has_gripper: Optional[bool] = None,
        encoder_resolution: Optional[int] = None,
    ):
        """
        Initialize the simulation backend.
        
        Can be initialized either with a RobotConfig object (preferred) or with
        explicit parameters. If robot_config is provided, its values are used
        as defaults, but explicit parameters will override them.
        
        Args:
            robot_config: Optional RobotConfig to get parameters from.
            num_joints: Number of logical joints to simulate (default: 6 or from robot_config).
            has_gripper: Whether to simulate a gripper (default: False or from robot_config).
            encoder_resolution: Encoder resolution to simulate (default: 4095 for 12-bit).
        """
        # Get defaults from robot_config if provided (supports both dict and RobotConfig object)
        if robot_config is not None:
            if isinstance(robot_config, dict):
                default_num_joints = robot_config.get('num_logical_joints', 6)
                default_has_gripper = robot_config.get('has_gripper', False)
            else:
                # Assume it's a RobotConfig object with attributes
                default_num_joints = robot_config.num_logical_joints
                default_has_gripper = robot_config.has_gripper
        else:
            # No robot config provided - require explicit parameters
            if num_joints is None:
                raise ValueError("SimulationBackend requires either robot_config or explicit num_joints parameter")
            default_num_joints = num_joints
            default_has_gripper = False
        
        # For encoder resolution, get from the active servo backend via registry
        from .backends import registry as backend_registry
        default_encoder_resolution = backend_registry.get_encoder_resolution()
        
        # Apply overrides
        self._num_joints = num_joints if num_joints is not None else default_num_joints
        self._has_gripper = has_gripper if has_gripper is not None else default_has_gripper
        self._encoder_resolution = encoder_resolution if encoder_resolution is not None else default_encoder_resolution
        
        self._robot_config = robot_config
        self._positions = [0.0] * self._num_joints
        self._gripper_position = 0.0
        self._initialized = False
    
    def initialize(self) -> bool:
        self._initialized = True
        print(f"[Sim] Simulation backend initialized with {self._num_joints} joints")
        return True
    
    def shutdown(self) -> None:
        self._initialized = False
        print("[Sim] Simulation backend shut down")
    
    @property
    def num_joints(self) -> int:
        return self._num_joints
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def encoder_resolution(self) -> int:
        """Returns the configured encoder resolution."""
        return self._encoder_resolution
    
    def set_joint_positions(
        self,
        positions_rad: list[float],
        speed: float,
        acceleration: float,
    ) -> None:
        if len(positions_rad) != self._num_joints:
            raise ValueError(f"Expected {self._num_joints} positions, got {len(positions_rad)}")
        self._positions = list(positions_rad)
    
    def get_joint_positions(self, verbose: bool = False) -> list[float]:
        if verbose:
            print(f"[Sim] Current positions: {np.round(self._positions, 3)}")
        return list(self._positions)
    
    def prepare_sync_write_commands(
        self,
        positions_rad: list[float],
        speed: int = 4095,
        accel: int = 0,
    ) -> list[tuple]:
        # In simulation, just return the positions as-is
        return [(i, pos, speed, accel) for i, pos in enumerate(positions_rad)]
    
    def sync_write(self, commands: list[tuple]) -> None:
        # Update positions from the commands
        # Commands are in format [(servo_id, raw_pos, speed, accel), ...]
        # We need to map servo_id to joint index
        actuator_ids = self._robot_config.get('actuator_ids', []) if self._robot_config else []
        logical_to_physical = self._robot_config.get('logical_to_physical_map', {}) if self._robot_config else {}
        gripper_id = self._robot_config.get('gripper_actuator_id') if self._robot_config else None
        
        # Build reverse mapping: servo_id -> logical_joint_index
        servo_to_joint = {}
        for logical_idx, physical_indices in logical_to_physical.items():
            for phys_idx in physical_indices:
                if phys_idx < len(actuator_ids):
                    servo_id = actuator_ids[phys_idx]
                    servo_to_joint[servo_id] = logical_idx
        
        for servo_id_or_idx, raw_pos, _, _ in commands:
            # Check if it's a servo ID or already an index
            if servo_id_or_idx in servo_to_joint:
                joint_idx = servo_to_joint[servo_id_or_idx]
                if 0 <= joint_idx < self._num_joints:
                    # Convert raw position to radians for storage
                    center = self._encoder_resolution // 2
                    self._positions[joint_idx] = (raw_pos - center) * math.pi / center
            elif servo_id_or_idx == gripper_id:
                # Handle gripper
                center = self._encoder_resolution // 2
                self._gripper_position = (raw_pos - center) * math.pi / center
            elif 0 <= servo_id_or_idx < self._num_joints:
                # Fallback: treat as index for backward compatibility
                center = self._encoder_resolution // 2
                self._positions[servo_id_or_idx] = (raw_pos - center) * math.pi / center
    
    def sync_read_positions(self, servo_ids: list[int] = None, timeout_s: Optional[float] = None) -> dict[int, int]:
        # Return simulated raw values using configured encoder resolution
        # Keys are servo IDs (matching the real hardware behavior)
        center = self._encoder_resolution // 2
        scale = center / math.pi
        
        actuator_ids = self._robot_config.get('actuator_ids', []) if self._robot_config else []
        logical_to_physical = self._robot_config.get('logical_to_physical_map', {}) if self._robot_config else {}
        
        # Build mapping: servo_id -> logical_joint_index (just the primary servo per joint)
        servo_to_joint = {}
        for logical_idx, physical_indices in logical_to_physical.items():
            if physical_indices and physical_indices[0] < len(actuator_ids):
                servo_id = actuator_ids[physical_indices[0]]
                servo_to_joint[servo_id] = logical_idx
        
        result = {}
        target_ids = servo_ids if servo_ids else list(servo_to_joint.keys())
        
        for servo_id in target_ids:
            if servo_id in servo_to_joint:
                joint_idx = servo_to_joint[servo_id]
                if 0 <= joint_idx < len(self._positions):
                    result[servo_id] = int(self._positions[joint_idx] * scale + center)
        
        return result
    
    def raw_to_joint_positions(self, raw_positions: dict[int, int]) -> list[float]:
        result = [0.0] * self._num_joints
        center = self._encoder_resolution // 2
        scale = math.pi / center
        for idx, raw in raw_positions.items():
            if 0 <= idx < self._num_joints:
                result[idx] = (raw - center) * scale
        return result
    
    def set_single_actuator_position(
        self,
        actuator_id: int,
        position_rad: float,
        speed: int,
        accel: int,
    ) -> None:
        gripper_id = self._robot_config.get('gripper_actuator_id') if self._robot_config else 100
        if actuator_id == gripper_id and self._has_gripper:
            self._gripper_position = position_rad
            return
        
        # Map servo ID to joint index
        joint_idx = self._servo_id_to_joint_index(actuator_id)
        if joint_idx is not None and 0 <= joint_idx < self._num_joints:
            self._positions[joint_idx] = position_rad
    
    def read_single_actuator_position(self, actuator_id: int) -> Optional[int]:
        center = self._encoder_resolution // 2
        scale = center / math.pi
        gripper_id = self._robot_config.get('gripper_actuator_id') if self._robot_config else 100
        
        if actuator_id == gripper_id and self._has_gripper:
            return int(self._gripper_position * scale + center)
        
        # Map servo ID to joint index
        joint_idx = self._servo_id_to_joint_index(actuator_id)
        if joint_idx is not None and 0 <= joint_idx < self._num_joints:
            return int(self._positions[joint_idx] * scale + center)
        
        return None
    
    def _servo_id_to_joint_index(self, servo_id: int) -> Optional[int]:
        """Map a servo ID to its logical joint index."""
        if not self._robot_config:
            return servo_id if 0 <= servo_id < self._num_joints else None
        
        actuator_ids = self._robot_config.get('actuator_ids', [])
        logical_to_physical = self._robot_config.get('logical_to_physical_map', {})
        
        for logical_idx, physical_indices in logical_to_physical.items():
            for phys_idx in physical_indices:
                if phys_idx < len(actuator_ids) and actuator_ids[phys_idx] == servo_id:
                    return logical_idx
        return None
    
    def set_current_position_as_zero(self, actuator_id: int) -> bool:
        print(f"[Sim] Set zero for actuator {actuator_id}")
        return True
    
    def set_pid_gains(self, actuator_id: int, kp: int, ki: int, kd: int) -> bool:
        print(f"[Sim] Set PID for actuator {actuator_id}: Kp={kp}, Ki={ki}, Kd={kd}")
        return True
    
    def apply_joint_limits(self) -> bool:
        print("[Sim] Applied joint limits (simulated)")
        return True
    
    @property
    def has_gripper(self) -> bool:
        return self._has_gripper
    
    @property
    def gripper_actuator_id(self) -> Optional[int]:
        return 100 if self._has_gripper else None
    
    def get_gripper_position(self) -> Optional[float]:
        return self._gripper_position if self._has_gripper else None
    
    def get_present_actuator_ids(self) -> set[int]:
        ids = set(range(self._num_joints))
        if self._has_gripper:
            ids.add(100)
        return ids
    
    def ping_actuator(self, actuator_id: int) -> bool:
        return actuator_id in self.get_present_actuator_ids()

