POS_ZERO = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
POS_HOME = [0.0, -0.785, 0.785, 0.0, -0.785, 0.0]
POS_REST = [0.0, -1.4, 1.5, 0.0, 0.0, 0.0]

# Joint names in UI order
JOINT_NAMES = [
    "Base",
    "Shoulder",
    "Elbow",
    "Wrist 1",
    "Wrist 2",
    "Wrist 3",
    "Gripper",
]

# Default jog step options (degrees) shown in Joint Control
JOINT_JOG_STEPS_DEG = ["1", "5", "10", "20", "45"]

# Cartesian position jogging increments (millimeters)
POS_INCREMENT_OPTIONS_MM = ["1", "5", "10", "50", "100"]

# Orientation jogging increments (degrees)
ORI_INCREMENT_OPTIONS_DEG = ["1", "5", "15", "45"]