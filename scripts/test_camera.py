#!/usr/bin/env python3
"""
Test script for Pi Camera functionality in GradientOS.

This script demonstrates basic camera operations including:
- Camera initialization
- Image capture
- Object detection by color
- Image processing and display
"""

import sys
import os
import time
import argparse
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from gradient_os.vision import PiCameraDriver, ImageProcessor
    from gradient_os.vision.camera_driver import PICAMERA2_AVAILABLE, OPENCV_AVAILABLE
except ImportError as e:
    print(f"Error importing vision modules: {e}")
    print("Please ensure you're running from the project root and all dependencies are installed.")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_camera_initialization():
    """Test basic camera initialization and capture."""
    print("\n=== Testing Camera Initialization ===")

    if not PICAMERA2_AVAILABLE:
        print("❌ PiCamera2 not available. Please install with: pip install picamera2")
        return False

    try:
        # Initialize camera
        camera = PiCameraDriver(resolution=(640, 480), framerate=30)

        if not camera.initialize():
            print("❌ Failed to initialize camera")
            return False

        print("✅ Camera initialized successfully")

        # Capture a test image
        print("📸 Capturing test image...")
        image = camera.capture_image()

        if image is None:
            print("❌ Failed to capture image")
            return False

        print(f"✅ Image captured successfully: {image.shape}")

        # Get camera info
        info = camera.get_camera_info()
        print(f"📊 Camera info: {info}")

        # Clean up
        camera.close()
        print("🧹 Camera closed")

        return True

    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False


def test_image_processing():
    """Test image processing functionality."""
    print("\n=== Testing Image Processing ===")

    if not OPENCV_AVAILABLE:
        print("❌ OpenCV not available. Please install with: pip install opencv-python")
        return False

    try:
        processor = ImageProcessor()
        print("✅ ImageProcessor initialized")

        # Create a test image (we'll use the camera to get a real image)
        camera = PiCameraDriver(resolution=(640, 480), framerate=30)

        if not camera.initialize():
            print("❌ Could not initialize camera for image processing test")
            return False

        image = camera.capture_image()
        camera.close()

        if image is None:
            print("❌ Could not capture image for processing")
            return False

        # Test preprocessing
        processed = processor.preprocess_image(image, resize=(320, 240), blur=5)
        print(f"✅ Image preprocessed: {processed.shape}")

        # Test color detection (example: detect red objects)
        # HSV range for red color
        lower_red = (0, 50, 50)
        upper_red = (10, 255, 255)

        objects = processor.detect_objects_by_color(image, lower_red, upper_red)
        print(f"✅ Detected {len(objects)} red objects")

        if objects:
            largest = processor.find_largest_object(objects)
            print(f"📍 Largest object: {largest}")

        # Test edge detection
        edges = processor.detect_edges(image)
        print(f"✅ Edge detection completed: {edges.shape}")

        # Test image info
        info = processor.get_image_info(image)
        print(f"📊 Image info: {info}")

        return True

    except Exception as e:
        print(f"❌ Image processing test failed: {e}")
        return False


def test_camera_streaming():
    """Test camera streaming functionality."""
    print("\n=== Testing Camera Streaming ===")

    if not PICAMERA2_AVAILABLE or not OPENCV_AVAILABLE:
        print("❌ Required libraries not available for streaming test")
        return False

    frame_count = 0
    start_time = time.time()

    def frame_callback(frame):
        nonlocal frame_count
        frame_count += 1
        if frame_count % 30 == 0:  # Print every 30 frames
            fps = frame_count / (time.time() - start_time)
            print(f"FPS: {fps:.1f}")

    try:
        camera = PiCameraDriver(resolution=(640, 480), framerate=30)

        if not camera.initialize():
            print("❌ Failed to initialize camera for streaming")
            return False

        print("🎥 Starting camera streaming (5 seconds)...")
        if not camera.start_streaming(frame_callback):
            print("❌ Failed to start streaming")
            return False

        # Stream for 5 seconds
        time.sleep(5)

        camera.stop_streaming()
        camera.close()

        total_time = time.time() - start_time
        avg_fps = frame_count / total_time
        print(f"Average FPS: {avg_fps:.1f}")
        return True

    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test Pi Camera functionality")
    parser.add_argument('--test', choices=['init', 'processing', 'streaming', 'all'],
                       default='all', help='Which test to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("🤖 GradientOS Camera Test Suite")
    print("=" * 40)

    # Check library availability
    print(f"📚 PiCamera2 available: {'✅' if PICAMERA2_AVAILABLE else '❌'}")
    print(f"📚 OpenCV available: {'✅' if OPENCV_AVAILABLE else '❌'}")

    success_count = 0
    total_tests = 0

    # Run tests based on selection
    if args.test in ['init', 'all']:
        total_tests += 1
        if test_camera_initialization():
            success_count += 1

    if args.test in ['processing', 'all']:
        total_tests += 1
        if test_image_processing():
            success_count += 1

    if args.test in ['streaming', 'all']:
        total_tests += 1
        if test_camera_streaming():
            success_count += 1

    # Summary
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 All tests passed! Camera functionality is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check your camera setup and dependencies.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
