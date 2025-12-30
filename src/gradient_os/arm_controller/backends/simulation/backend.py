# backends/simulation/backend.py
#
# Simulation backend for GradientOS.
# Provides an in-memory simulation of the actuator system for development and testing.

from typing import Optional, TYPE_CHECKING
import math
import numpy as np

from ..registry import get_encoder_resolution
from ...actuator_interface import ActuatorBackend

if TYPE_CHECKING:
    from ...robots.base import RobotConfig


class SimulationBackend(ActuatorBackend):
    """
    In-memory simulation backend for development and testing.
    
    This backend simulates the behavior of physical actuators without requiring
    actual hardware. It's useful for:
    - Development and debugging of motion planning algorithms
    - Testing trajectory execution logic
    - Running the controller UI without a physical robot
    
    The simulation maintains joint positions in radians internally and converts
    to/from raw encoder values as needed to match the interface expected by
    other parts of the system.
    """
    
    def __init__(
        self,
        robot_config: Optional[dict] = None,
        num_joints: Optional[int] = None,
        has_gripper: Optional[bool] = None,
        encoder_resolution: Optional[int] = None,
    ):
        """
        Initialize the simulation backend.
        
        Can be initialized either with a robot_config dict (preferred) or with
        explicit parameters. If robot_config is provided, its values are used
        as defaults, but explicit parameters will override them.
        
        Args:
            robot_config: Optional dict from RobotConfig.get_config_dict() to get parameters from.
            num_joints: Number of logical joints to simulate (default: 6 or from robot_config).
            has_gripper: Whether to simulate a gripper (default: False or from robot_config).
            encoder_resolution: Encoder resolution to simulate (default: 4095 for 12-bit).
        """
        # Get defaults from robot_config if provided
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
        try:
            default_encoder_resolution = get_encoder_resolution()
        except Exception:
            default_encoder_resolution = 4095  # Fallback to common 12-bit encoder
        
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

