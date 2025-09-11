#!/usr/bin/env python3
import sys
import os
import time
import threading
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import io

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gradient_os.vision import PiCameraDriver  # noqa: E402

latest_jpeg_lock = threading.Lock()
# In single-camera mode, latest_jpeg_single is used.
latest_jpeg_single = None
# In dual-camera mode, latest_jpeg_map is used with keys 0 and 1.
latest_jpeg_map = {0: None, 1: None}
_both_mode = False


def encode_jpeg(frame, quality: int = 80):
    try:
        import cv2
        q = max(30, min(95, int(quality)))
        ret, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), q])
        if not ret:
            return None
        return buf.tobytes()
    except Exception:
        return None


class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _both_mode
        if not _both_mode and self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    global latest_jpeg_single
                    with latest_jpeg_lock:
                        jpeg = latest_jpeg_single
                    if jpeg is None:
                        time.sleep(0.01)
                        continue
                    self.wfile.write(b'--FRAME\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(b'Content-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n')
                    self.wfile.write(jpeg)
                    self.wfile.write(b'\r\n')
            except BrokenPipeError:
                pass
            except Exception:
                pass
        elif _both_mode and self.path in ('/cam0.mjpg', '/cam1.mjpg'):
            cam_idx = 0 if 'cam0' in self.path else 1
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    global latest_jpeg_map
                    with latest_jpeg_lock:
                        jpeg = latest_jpeg_map.get(cam_idx)
                    if jpeg is None:
                        time.sleep(0.01)
                        continue
                    self.wfile.write(b'--FRAME\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(b'Content-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n')
                    self.wfile.write(jpeg)
                    self.wfile.write(b'\r\n')
            except BrokenPipeError:
                pass
            except Exception:
                pass
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            if _both_mode:
                page = (
                    "<html><body style='background-color: black; color: white;'>"
                    "<h1>GradientOS Dual Camera Stream</h1>"
                    "<div style='display:flex;flex-direction:column;gap:10px;'>"
                    "<div><h3>Camera 0</h3><img src='/cam0.mjpg'/></div>"
                    "<div><h3>Camera 1</h3><img src='/cam1.mjpg'/></div>"
                    "</div>"
                    "</body></html>"
                )
                self.wfile.write(page.encode('utf-8'))
            else:
                self.wfile.write(b"<html><body style='background-color: black; color: white;'>" \
                                 b"<h1>GradientOS Camera Stream</h1>" \
                                 b"<img src='/stream.mjpg'/>" \
                                 b"</body></html>")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description='MJPEG camera streamer')
    parser.add_argument('--camera', type=int, default=0, help='Camera index (0 or 1)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Bind address')
    parser.add_argument('--port', type=int, default=8080, help='HTTP port')
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--fps', type=int, default=15)
    parser.add_argument('--jpeg-quality', type=int, default=80, help='MJPEG quality (30-95)')
    parser.add_argument('--vflip', action='store_true', help='Flip image vertically')
    parser.add_argument('--hflip', action='store_true', help='Flip image horizontally')
    parser.add_argument('--both', action='store_true', help='Stream both cameras on one server')
    args = parser.parse_args()

    global _both_mode
    _both_mode = args.both

    cams = []
    if args.both:
        # Start both camera streams
        for cam_idx in (0, 1):
            cam = PiCameraDriver(camera_id=cam_idx, resolution=(args.width, args.height), framerate=args.fps)
            if not cam.initialize():
                print(f'[cam{cam_idx}] Failed to initialize camera')
                cams.append(None)
                continue

            def make_cb(idx):
                def on_frame(frame):
                    # Optional flips
                    try:
                        import cv2
                        if args.vflip and args.hflip:
                            frame_flipped = cv2.flip(frame, -1)
                        elif args.vflip:
                            frame_flipped = cv2.flip(frame, 0)
                        elif args.hflip:
                            frame_flipped = cv2.flip(frame, 1)
                        else:
                            frame_flipped = frame
                    except Exception:
                        frame_flipped = frame

                    jpeg = encode_jpeg(frame_flipped, args.jpeg_quality)
                    if jpeg is None:
                        return
                    with latest_jpeg_lock:
                        latest_jpeg_map[idx] = jpeg
                return on_frame

            if not cam.start_streaming(make_cb(cam_idx)):
                print(f'[cam{cam_idx}] Failed to start streaming')
                cams.append(None)
                try:
                    cam.close()
                except Exception:
                    pass
                continue
            cams.append(cam)
        if cams[0] is None and cams[1] is None:
            print('No cameras streaming. Exiting.')
            sys.exit(1)
    else:
        # Single camera mode
        cam = PiCameraDriver(camera_id=args.camera, resolution=(args.width, args.height), framerate=args.fps)
        if not cam.initialize():
            print('Failed to initialize camera')
            sys.exit(1)

        def on_frame_single(frame):
            global latest_jpeg_single
            # Optional flips
            try:
                import cv2
                if args.vflip and args.hflip:
                    frame_flipped = cv2.flip(frame, -1)
                elif args.vflip:
                    frame_flipped = cv2.flip(frame, 0)
                elif args.hflip:
                    frame_flipped = cv2.flip(frame, 1)
                else:
                    frame_flipped = frame
            except Exception:
                frame_flipped = frame

            jpeg = encode_jpeg(frame_flipped, args.jpeg_quality)
            if jpeg is None:
                return
            with latest_jpeg_lock:
                latest_jpeg_single = jpeg

        cam.start_streaming(on_frame_single)
        cams = [cam]

    server = ThreadedHTTPServer((args.host, args.port), StreamingHandler)
    if args.both:
        print(f"Serving MJPEG (cam0=/cam0.mjpg, cam1=/cam1.mjpg) on http://{args.host}:{args.port}/")
    else:
        print(f"Serving MJPEG on http://{args.host}:{args.port}/ (camera {args.camera})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for c in cams:
            try:
                if c is not None:
                    c.stop_streaming()
                    c.close()
            except Exception:
                pass


if __name__ == '__main__':
    main()
