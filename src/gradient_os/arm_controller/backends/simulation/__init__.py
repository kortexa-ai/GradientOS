# backends/simulation/__init__.py
#
# Simulation backend for GradientOS - no hardware required.
# Useful for development, testing, and debugging.

from .backend import SimulationBackend

__all__ = ['SimulationBackend']

