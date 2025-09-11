"""
Pi Camera driver for GradientOS.

This module provides a high-level interface for controlling Raspberry Pi cameras,
including initialization, configuration, image capture, and video streaming.
"""

import time
import threading
from typing import Optional, Tuple, Callable, List, Dict
import logging

try:
    from picamera2 import Picamera2
    from libcamera import controls
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    print("Warning: picamera2 not available. Install with: pip install picamera2")

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("Warning: OpenCV not available. Install with: pip install opencv-python")

logger = logging.getLogger(__name__)


class PiCameraDriver:
    """
    Driver class for Raspberry Pi Camera operations.

    This class provides methods for:
    - Camera initialization and configuration
    - Image capture (still images and video)
    - Camera parameter adjustment
    - Streaming capabilities
    """

    def __init__(self, camera_id: int = 0, resolution: Tuple[int, int] = (640, 480), framerate: int = 30):
        """
        Initialize the Pi Camera driver.

        Args:
            camera_id (int): Camera device ID (0 for default camera)
            resolution (Tuple[int, int]): Camera resolution as (width, height)
            framerate (int): Camera framerate in FPS
        """
        self.camera_id = camera_id
        self.resolution = resolution
        self.framerate = framerate

        self.camera: Optional[Picamera2] = None
        self.is_streaming = False
        self.stream_thread: Optional[threading.Thread] = None
        self.stream_callback: Optional[Callable] = None

        if not PICAMERA2_AVAILABLE:
            raise ImportError("picamera2 is required for Pi Camera functionality")

        logger.info(f"PiCameraDriver initialized with camera {camera_id}, resolution {resolution}, framerate {framerate}")

    @staticmethod
    def list_cameras() -> List[Dict]:
        """
        Return information about all detected cameras.

        Returns:
            list[dict]: List of camera info dictionaries as reported by Picamera2
        """
        if not PICAMERA2_AVAILABLE:
            return []

        try:
            return Picamera2.global_camera_info()
        except Exception as e:
            logger.error(f"Failed to enumerate cameras: {e}")
            return []

    def initialize(self) -> bool:
        """
        Initialize the camera hardware and configure settings.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Validate that at least one camera is present
            available_cameras = self.list_cameras()
            if not available_cameras:
                logger.error("No cameras detected by libcamera/Picamera2. Check cabling, power, and overlays.")
                return False

            if self.camera_id < 0 or self.camera_id >= len(available_cameras):
                logger.error(f"Requested camera_id {self.camera_id} is out of range. "
                             f"Detected cameras: {len(available_cameras)}")
                for idx, info in enumerate(available_cameras):
                    logger.error(f" - [{idx}] {info}")
                return False

            self.camera = Picamera2(self.camera_id)

            # Configure camera settings
            config = self.camera.create_still_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                controls={"FrameRate": self.framerate}
            )

            self.camera.configure(config)
            self.camera.start()

            logger.info("Camera initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

    def capture_image(self) -> Optional['numpy.ndarray']:
        """
        Capture a single image from the camera.

        Returns:
            numpy.ndarray: Captured image as numpy array, or None if capture failed
        """
        if not self.camera:
            logger.error("Camera not initialized")
            return None

        try:
            # Capture image
            image = self.camera.capture_array()

            logger.debug("Image captured successfully")
            return image

        except Exception as e:
            logger.error(f"Failed to capture image: {e}")
            return None

    def set_exposure(self, exposure_time_us: int) -> bool:
        """
        Set camera exposure time.

        Args:
            exposure_time_us (int): Exposure time in microseconds

        Returns:
            bool: True if setting applied successfully
        """
        if not self.camera:
            return False

        try:
            self.camera.set_controls({"ExposureTime": exposure_time_us})
            logger.info(f"Exposure time set to {exposure_time_us} μs")
            return True
        except Exception as e:
            logger.error(f"Failed to set exposure: {e}")
            return False

    def set_gain(self, analogue_gain: float) -> bool:
        """
        Set camera analogue gain.

        Args:
            analogue_gain (float): Analogue gain value

        Returns:
            bool: True if setting applied successfully
        """
        if not self.camera:
            return False

        try:
            self.camera.set_controls({"AnalogueGain": analogue_gain})
            logger.info(f"Analogue gain set to {analogue_gain}")
            return True
        except Exception as e:
            logger.error(f"Failed to set gain: {e}")
            return False

    def start_streaming(self, callback: Callable[['numpy.ndarray'], None]) -> bool:
        """
        Start streaming camera frames to a callback function.

        Args:
            callback: Function to call with each frame (receives numpy array)

        Returns:
            bool: True if streaming started successfully
        """
        if not self.camera or self.is_streaming:
            return False

        self.stream_callback = callback
        self.is_streaming = True

        self.stream_thread = threading.Thread(target=self._streaming_loop, daemon=True)
        self.stream_thread.start()

        logger.info("Camera streaming started")
        return True

    def stop_streaming(self) -> bool:
        """
        Stop camera streaming.

        Returns:
            bool: True if streaming stopped successfully
        """
        if not self.is_streaming:
            return False

        self.is_streaming = False

        if self.stream_thread:
            self.stream_thread.join(timeout=1.0)

        logger.info("Camera streaming stopped")
        return True

    def _streaming_loop(self):
        """Internal streaming loop that captures and sends frames to callback."""
        while self.is_streaming and self.camera:
            try:
                frame = self.camera.capture_array()
                if self.stream_callback:
                    self.stream_callback(frame)
                time.sleep(1.0 / self.framerate)  # Control frame rate
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                break

    def get_camera_info(self) -> dict:
        """
        Get information about the camera.

        Returns:
            dict: Camera information dictionary
        """
        info = {
            "camera_id": self.camera_id,
            "resolution": self.resolution,
            "framerate": self.framerate,
            "initialized": self.camera is not None,
            "streaming": self.is_streaming,
            "picamera2_available": PICAMERA2_AVAILABLE,
            "opencv_available": OPENCV_AVAILABLE
        }
        return info

    def close(self):
        """Close the camera and clean up resources."""
        self.stop_streaming()

        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
                self.camera = None
                logger.info("Camera closed successfully")
            except Exception as e:
                logger.error(f"Error closing camera: {e}")
