# arm_controller package
#
# This package provides robot arm control functionality for GradientOS.
#
# Architecture:
# -------------
# - actuator_interface.py: Abstract base class for actuator backends
# - backends/: Servo/actuator backend implementations (Feetech, etc.)
# - robots/: Robot-specific configurations (gradient0, gradient0_5, etc.)
# - robot_config.py: Backward-compatible config re-exports
# - utils.py: Shared utilities and global state (backward-compatible)
# - servo_driver.py: High-level servo control (backward-compatible)
# - servo_protocol.py: Low-level protocol (backward-compatible, delegates to backends)
# - command_api.py: UDP command handlers
# - trajectory_execution.py: Trajectory planning and execution
#
# For new robot integrations:
# 1. Create a new robot config in robots/ (inherit from RobotConfig)
# 2. Use the appropriate actuator backend (e.g., FeetechBackend)
# 3. Initialize with your robot's configuration
#
# Example:
# ```python
# from gradient_os.arm_controller import FeetechBackend
# from gradient_os.arm_controller.robots import Gradient0Config
#
# robot = Gradient0Config()
# backend = FeetechBackend(robot)
# backend.initialize()
# backend.set_joint_positions([0, 0, 0, 0, 0, 0], speed=500, acceleration=100)
# ```

# Import actuator interface
from .actuator_interface import ActuatorBackend, SimulationBackend

# Import backends
from .backends import FeetechBackend

# Import robot configuration classes
from .robots import RobotConfig, Gradient0Config, get_robot_config, list_available_robots

# Import backward-compatible robot config module
from . import robot_config

# Import backward-compatible modules
from . import utils
from . import servo_driver
from . import servo_protocol
from . import command_api
from . import trajectory_execution

__all__ = [
    # Interface
    'ActuatorBackend',
    'SimulationBackend',
    # Backends
    'FeetechBackend',
    # Robot Configuration
    'RobotConfig',
    'Gradient0Config',
    'get_robot_config',
    'list_available_robots',
    # Legacy configuration module
    'robot_config',
    # Legacy modules (backward compatible)
    'utils',
    'servo_driver',
    'servo_protocol',
    'command_api',
    'trajectory_execution',
]
