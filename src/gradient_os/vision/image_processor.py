"""
Image processing utilities for GradientOS vision system.

This module provides computer vision functionality for:
- Image preprocessing and filtering
- Object detection and tracking
- Color space conversions
- Basic feature extraction
"""

import numpy as np
import logging
from typing import Optional, Tuple, List, Dict, Any

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("Warning: OpenCV not available. Install with: pip install opencv-python")

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Image processing class for computer vision tasks.

    Provides methods for image preprocessing, object detection,
    and feature extraction useful for robotic applications.
    """

    def __init__(self):
        """Initialize the image processor."""
        if not OPENCV_AVAILABLE:
            raise ImportError("OpenCV is required for image processing functionality")

        logger.info("ImageProcessor initialized")

    def preprocess_image(self, image: np.ndarray,
                        resize: Optional[Tuple[int, int]] = None,
                        normalize: bool = True,
                        blur: Optional[int] = None) -> np.ndarray:
        """
        Preprocess an image for computer vision tasks.

        Args:
            image: Input image as numpy array
            resize: Optional tuple (width, height) to resize image
            normalize: Whether to normalize pixel values to [0, 1]
            blur: Optional kernel size for Gaussian blur

        Returns:
            Processed image as numpy array
        """
        processed = image.copy()

        # Resize if requested
        if resize:
            processed = cv2.resize(processed, resize, interpolation=cv2.INTER_LINEAR)

        # Apply blur if requested
        if blur:
            processed = cv2.GaussianBlur(processed, (blur, blur), 0)

        # Normalize if requested
        if normalize:
            processed = processed.astype(np.float32) / 255.0

        return processed

    def detect_objects_by_color(self, image: np.ndarray,
                               lower_bound: Tuple[int, int, int],
                               upper_bound: Tuple[int, int, int],
                               min_area: int = 100) -> List[Dict[str, Any]]:
        """
        Detect objects in image based on color range.

        Args:
            image: Input image in BGR format
            lower_bound: Lower HSV bound as (H, S, V)
            upper_bound: Upper HSV bound as (H, S, V)
            min_area: Minimum contour area to consider as object

        Returns:
            List of detected objects with position, size, and center coordinates
        """
        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Create mask for color range
        mask = cv2.inRange(hsv, np.array(lower_bound), np.array(upper_bound))

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2

                objects.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'center_x': center_x,
                    'center_y': center_y,
                    'area': area
                })

        logger.debug(f"Detected {len(objects)} objects by color")
        return objects

    def find_largest_object(self, objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the largest object from a list of detected objects.

        Args:
            objects: List of detected objects

        Returns:
            Largest object dictionary or None if no objects
        """
        if not objects:
            return None

        return max(objects, key=lambda obj: obj['area'])

    def draw_bounding_boxes(self, image: np.ndarray,
                           objects: List[Dict[str, Any]],
                           color: Tuple[int, int, int] = (0, 255, 0),
                           thickness: int = 2) -> np.ndarray:
        """
        Draw bounding boxes around detected objects on image.

        Args:
            image: Input image
            objects: List of objects with bounding box info
            color: BGR color tuple for bounding boxes
            thickness: Line thickness for bounding boxes

        Returns:
            Image with bounding boxes drawn
        """
        result = image.copy()

        for obj in objects:
            cv2.rectangle(result,
                         (obj['x'], obj['y']),
                         (obj['x'] + obj['width'], obj['y'] + obj['height']),
                         color, thickness)

            # Draw center point
            cv2.circle(result, (obj['center_x'], obj['center_y']), 3, (0, 0, 255), -1)

        return result

    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        Convert image to grayscale.

        Args:
            image: Input image

        Returns:
            Grayscale image
        """
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def apply_threshold(self, image: np.ndarray,
                       threshold: int = 127,
                       max_value: int = 255,
                       threshold_type: int = cv2.THRESH_BINARY) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply thresholding to image.

        Args:
            image: Input grayscale image
            threshold: Threshold value
            max_value: Maximum value for THRESH_BINARY
            threshold_type: OpenCV threshold type

        Returns:
            Tuple of (thresholded_image, threshold_value)
        """
        if len(image.shape) > 2:
            gray = self.convert_to_grayscale(image)
        else:
            gray = image

        _, thresh = cv2.threshold(gray, threshold, max_value, threshold_type)
        return thresh, _

    def detect_edges(self, image: np.ndarray,
                    threshold1: int = 50,
                    threshold2: int = 150) -> np.ndarray:
        """
        Detect edges in image using Canny edge detection.

        Args:
            image: Input image (will be converted to grayscale if needed)
            threshold1: First threshold for hysteresis
            threshold2: Second threshold for hysteresis

        Returns:
            Edge-detected image
        """
        if len(image.shape) > 2:
            gray = self.convert_to_grayscale(image)
        else:
            gray = image

        edges = cv2.Canny(gray, threshold1, threshold2)
        return edges

    def save_image(self, image: np.ndarray, filepath: str) -> bool:
        """
        Save image to file.

        Args:
            image: Image to save
            filepath: Path to save image

        Returns:
            True if save successful, False otherwise
        """
        try:
            cv2.imwrite(filepath, image)
            logger.info(f"Image saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return False

    def get_image_info(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Get information about an image.

        Args:
            image: Input image

        Returns:
            Dictionary with image information
        """
        info = {
            'shape': image.shape,
            'dtype': str(image.dtype),
            'channels': image.shape[2] if len(image.shape) > 2 else 1,
            'height': image.shape[0],
            'width': image.shape[1] if len(image.shape) > 1 else image.shape[0],
            'total_pixels': image.size
        }
        return info
