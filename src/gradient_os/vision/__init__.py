"""
Vision module for GradientOS - handles camera operations and computer vision tasks.

This module provides functionality for:
- Pi Camera initialization and configuration
- Image capture and streaming
- Basic computer vision processing
- Camera calibration utilities
"""

from .camera_driver import PiCameraDriver
from .image_processor import ImageProcessor
from .cli import main as vision_cli_main

__all__ = ['PiCameraDriver', 'ImageProcessor', 'vision_cli_main']
