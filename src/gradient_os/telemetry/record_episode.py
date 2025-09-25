import argparse
import json
import socket
import time
from pathlib import Path
from typing import Optional, Tuple
import subprocess
import sys
import requests

import cv2
from typing import Callable
try:
    from PIL import Image  # fallback for saving
except Exception:
    Image = None  # type: ignore
import numpy as np

from .mjpeg import MjpegStream


def _parse_hostport(value: str) -> Tuple[str, int]:
    host, port = value.rsplit(":", 1)
    return host, int(port)


def _start_udp_listener(bind: Optional[str]) -> Optional[socket.socket]:
    if not bind:
        return None
    host, port = _parse_hostport(bind)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.setblocking(False)
    return sock


def _recv_latest_json(sock: Optional[socket.socket]) -> Optional[dict]:
    if sock is None:
        return None
    data = None
    while True:
        try:
            buf, _ = sock.recvfrom(65536)
            data = buf
        except (BlockingIOError, InterruptedError):
            break
        except Exception:
            break
    if data is None:
        return None
    try:
        return json.loads(data.decode("utf-8", errors="ignore"))
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes-dir", type=str, default="recorded_episodes")
    ap.add_argument("--prompt", type=str, default="")
    ap.add_argument("--base-cam", type=str, required=False)
    ap.add_argument("--wrist-cam", type=str, required=False)
    # Output sizing: by default, do not resize (use camera server size). Enable only if explicitly set.
    ap.add_argument("--out-width", type=int, default=0)
    ap.add_argument("--out-height", type=int, default=0)
    ap.add_argument("--resize", type=int, default=0)
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--state-udp", type=str, default="0.0.0.0:5555")
    ap.add_argument("--action-udp", type=str, default="")
    # Cameras ON by default; allow disabling
    ap.add_argument("--no-cameras", action="store_true",
                    help="Disable camera recording (no MJPEG start, no frame saving)")
    # If set, do not auto-start MJPEG even if URLs are absent (controller will manage cameras)
    ap.add_argument("--no-mjpeg-autostart", action="store_true")
    ap.add_argument("--mjpeg-host", type=str, default="127.0.0.1")
    ap.add_argument("--mjpeg-port", type=int, default=8080)
    ap.add_argument("--mjpeg-width", type=int, default=640)
    ap.add_argument("--mjpeg-height", type=int, default=480)
    ap.add_argument("--mjpeg-fps", type=int, default=30)
    ap.add_argument("--mjpeg-quality", type=int, default=80)
    # Recorder will default to dual endpoints; MJPEG server will gracefully handle 1 or 2 cameras
    ap.add_argument("--mjpeg-vflip", action="store_true")
    ap.add_argument("--mjpeg-hflip", action="store_true")
    args = ap.parse_args()

    episodes_root = Path(args.episodes_dir).expanduser()
    # Default episodes dir to project-level /recorded_episodes if user passes that path
    episodes_root.mkdir(parents=True, exist_ok=True)
    ep_dir = episodes_root / time.strftime("%Y%m%d_%H%M%S"); ep_dir.mkdir(parents=True, exist_ok=True)
    img_base_dir = ep_dir / "base"; img_wrist_dir = ep_dir / "wrist"
    img_base_dir.mkdir(exist_ok=True); img_wrist_dir.mkdir(exist_ok=True)

    # Simple file logger into the episode dir for debugging when run under controller (stdout suppressed)
    log_f = open(ep_dir / "recorder.log", "a", encoding="utf-8")
    def _log(msg: str) -> None:
        try:
            ts = time.strftime("%H:%M:%S")
            line = f"[{ts}] {msg}"
            print(line)
            log_f.write(line + "\n"); log_f.flush()
        except Exception:
            pass

    meta = {
        "prompt": args.prompt, "fps": int(args.fps),
        "out_width": int(args.out_width), "out_height": int(args.out_height), "resize": int(args.resize),
        "base_cam": args.base_cam, "wrist_cam": args.wrist_cam,
        "state_udp": args.state_udp, "action_udp": (args.action_udp or None),
    }
    (ep_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    steps_f = open(ep_dir / "steps.jsonl", "w", encoding="utf-8")

    # Normalize sentinel values for disabling cameras
    if isinstance(args.base_cam, str) and args.base_cam.lower() in {"off", "none", "disabled"}:
        args.base_cam = None
    if isinstance(args.wrist_cam, str) and args.wrist_cam.lower() in {"off", "none", "disabled"}:
        args.wrist_cam = None

    # Optionally start MJPEG camera server if camera URLs were not provided (default behavior)
    mjpeg_proc: Optional[subprocess.Popen] = None
    base_url = args.base_cam
    wrist_url = args.wrist_cam

    def _build_urls(host: str, port: int, both: bool) -> Tuple[str, Optional[str]]:
        if both:
            # Note: On this platform, cam indices appear inverted versus physical mounting.
            # Map base → cam1, wrist → cam0 to ensure files land in correct folders.
            return (f"http://{host}:{port}/cam1.mjpg", f"http://{host}:{port}/cam0.mjpg")
        return (f"http://{host}:{port}/stream.mjpg", None)

    auto_enable_cams = not bool(args.no_cameras)
    # Start MJPEG server if cameras enabled and no explicit URL provided
    if (not base_url) and auto_enable_cams and (not args.no_mjpeg_autostart):
        cmd = [
            sys.executable, "-m", "gradient_os.vision", "mjpeg",
            "--host", str(args.mjpeg_host),
            "--port", str(args.mjpeg_port),
            "--width", str(args.mjpeg_width),
            "--height", str(args.mjpeg_height),
            "--fps", str(args.mjpeg_fps),
            "--jpeg-quality", str(args.mjpeg_quality),
        ]
        if args.mjpeg_vflip:
            cmd.append("--vflip")
        if args.mjpeg_hflip:
            cmd.append("--hflip")
        # Force dual endpoints so recorder can always attempt two streams
        cmd.append("--both")

        try:
            mjpeg_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            # Give the server a brief moment to start
            time.sleep(1.0)
            bu, wu = _build_urls(args.mjpeg_host, args.mjpeg_port, True)
            base_url = base_url or bu
            wrist_url = wrist_url or wu
            _log(f"Started MJPEG server on http://{args.mjpeg_host}:{args.mjpeg_port}/")
        except Exception as e:
            _log(f"⚠️ Failed to start MJPEG server automatically: {e}")
            mjpeg_proc = None

    # If cameras are disabled or URLs still not provided, skip creating streams
    if args.no_cameras:
        base_url = None
        wrist_url = None
    else:
        # Fall back to dual endpoints on localhost; server may expose only cam0 if single camera
        if not base_url:
            base_url, wrist_url_fallback = _build_urls("127.0.0.1", 8080, True)
            wrist_url = wrist_url or wrist_url_fallback
            _log(f"No --base-cam provided. Falling back to {base_url} (and {wrist_url or 'None'})")

        # Verify URLs respond; try sensible fallbacks
        def _url_ok(url: Optional[str]) -> bool:
            if not url:
                return False
            try:
                r = requests.get(url, stream=True, timeout=2.0)
                ok = (200 <= r.status_code < 300)
                try:
                    r.close()
                except Exception:
                    pass
                return ok
            except Exception:
                return False

        def _try_fallback(url: Optional[str]) -> Optional[str]:
            if not url:
                return None
            if url.endswith("/cam0.mjpg"):
                alt = url.rsplit("/", 1)[0] + "/stream.mjpg"
                return alt if _url_ok(alt) else None
            if url.endswith("/stream.mjpg"):
                alt = url.rsplit("/", 1)[0] + "/cam0.mjpg"
                return alt if _url_ok(alt) else None
            return None

        if base_url and not _url_ok(base_url):
            alt = _try_fallback(base_url)
            if alt:
                _log(f"Base cam URL not ready; falling back to {alt}")
                base_url = alt
            else:
                _log("Base cam URL not ready yet; will keep trying in background")
        if wrist_url and not _url_ok(wrist_url):
            alt = _try_fallback(wrist_url)
            if alt:
                _log(f"Wrist cam URL not ready; falling back to {alt}")
                wrist_url = alt
            else:
                _log("Wrist cam URL not ready yet; will keep trying in background")

    base_stream = MjpegStream(base_url) if base_url else None
    wrist_stream = MjpegStream(wrist_url) if wrist_url else None

    def _wait_for_stream(stream: Optional[MjpegStream], name: str, timeout_s: float = 8.0) -> bool:
        if stream is None:
            return False
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            ok, img = stream.read()
            if ok and img is not None:
                _log(f"{name} camera is delivering frames")
                return True
            time.sleep(0.02)
        _log(f"{name} camera not ready within {timeout_s:.1f}s")
        return False

    # Probe once so first frames are likely available before entering loop
    _ = _wait_for_stream(base_stream, "Base")
    _ = _wait_for_stream(wrist_stream, "Wrist")

    def _save_image_rgb(path: Path, rgb: np.ndarray) -> bool:
        try:
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            bgr = rgb
        try:
            ok = cv2.imwrite(str(path), bgr)
            if ok:
                return True
        except Exception:
            pass
        # Fallback to PIL if available
        if Image is not None:
            try:
                img = Image.fromarray(rgb)
                img.save(str(path), format="JPEG", quality=90)
                return True
            except Exception:
                return False
        return False
    state_sock = _start_udp_listener(args.state_udp)
    action_sock = _start_udp_listener(args.action_udp or None)

    # Determine target output size only if requested; otherwise keep native
    target_w = int(args.out_width) if int(args.out_width) > 0 else int(args.resize)
    target_h = int(args.out_height) if int(args.out_height) > 0 else int(args.resize)

    def _center_crop_to_aspect(img: np.ndarray, target_aspect: float) -> np.ndarray:
        h, w = img.shape[:2]
        aspect = w / float(h)
        if abs(aspect - target_aspect) < 1e-3:
            return img
        if aspect > target_aspect:
            # Too wide: crop width
            new_w = int(round(h * target_aspect))
            x0 = (w - new_w) // 2
            return img[:, x0:x0+new_w]
        else:
            # Too tall: crop height
            new_h = int(round(w / target_aspect))
            y0 = (h - new_h) // 2
            return img[y0:y0+new_h, :]

    def _prep(img: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if img is None: return None
        # If no target specified, return native
        if target_w <= 0 or target_h <= 0:
            return img
        # Aspect-preserving center-crop, then resize
        target_aspect = target_w / float(target_h)
        cropped = _center_crop_to_aspect(img, target_aspect)
        if cropped.shape[1] != target_w or cropped.shape[0] != target_h:
            cropped = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)
        return cropped

    period = 1.0 / max(1, int(args.fps)); step = 0
    _log(f"Recording to {ep_dir} (Ctrl+C to stop)")
    first_base_ok = False
    first_wrist_ok = False
    first_wait_logged = False
    start_time = time.time()
    try:
        while True:
            t0 = time.time(); ts = time.time()
            ok_b, base_img = (base_stream.read() if base_stream else (False, None))
            ok_w, wrist_img = (wrist_stream.read() if wrist_stream else (False, None))
            base_img = _prep(base_img) if ok_b else None
            wrist_img = _prep(wrist_img) if ok_w else None

            # One-time connect logs
            if ok_b and not first_base_ok:
                _log("Base camera frames started")
                first_base_ok = True
            if ok_w and not first_wrist_ok:
                _log("Wrist camera frames started")
                first_wrist_ok = True
            if (not first_base_ok and not first_wrist_ok) and not first_wait_logged and (time.time() - start_time) > 2.0:
                _log("Waiting for camera frames...")
                first_wait_logged = True

            state_msg = _recv_latest_json(state_sock)
            action_msg = _recv_latest_json(action_sock)

            base_fn = wrist_fn = None
            if base_img is not None:
                base_fn = f"{step:06d}.jpg"
                saved = _save_image_rgb(img_base_dir / base_fn, base_img)
                if not saved:
                    _log(f"WARNING: failed to write base frame {base_fn}")
                    base_fn = None
            if wrist_img is not None:
                wrist_fn = f"{step:06d}.jpg"
                saved = _save_image_rgb(img_wrist_dir / wrist_fn, wrist_img)
                if not saved:
                    _log(f"WARNING: failed to write wrist frame {wrist_fn}")
                    wrist_fn = None

            row = {
                "t": ts, "base": base_fn, "wrist": wrist_fn,
                "state": (state_msg or {}), "action": (action_msg or {}).get("action"),
                "prompt": args.prompt,
            }
            steps_f.write(json.dumps(row) + "\n"); steps_f.flush()

            step += 1
            dt = time.time() - t0
            time.sleep(max(0.0, period - dt))
    except KeyboardInterrupt:
        pass
    finally:
        steps_f.close()
        try: log_f.close()
        except Exception: pass
        for s in (base_stream, wrist_stream):
            try: s and s.close()
            except Exception: pass
        for sk in (state_sock, action_sock):
            try: sk and sk.close()
            except Exception: pass
        if mjpeg_proc is not None:
            try:
                mjpeg_proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()


