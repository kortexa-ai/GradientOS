# backends/feetech/__init__.py
#
# Feetech STS/SCS series servo backend for GradientOS.
# This module provides hardware control for Feetech serial bus servos.

from .driver import FeetechBackend
from . import protocol
from . import config

__all__ = ['FeetechBackend', 'protocol', 'config']

