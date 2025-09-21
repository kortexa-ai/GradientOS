import argparse
import json
import socket
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
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
    ap.add_argument("--resize", type=int, default=256)
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--state-udp", type=str, default="0.0.0.0:5555")
    ap.add_argument("--action-udp", type=str, default="")
    args = ap.parse_args()

    episodes_root = Path(args.episodes_dir).expanduser()
    # Default episodes dir to project-level /recorded_episodes if user passes that path
    episodes_root.mkdir(parents=True, exist_ok=True)
    ep_dir = episodes_root / time.strftime("%Y%m%d_%H%M%S"); ep_dir.mkdir(parents=True, exist_ok=True)
    img_base_dir = ep_dir / "base"; img_wrist_dir = ep_dir / "wrist"
    img_base_dir.mkdir(exist_ok=True); img_wrist_dir.mkdir(exist_ok=True)

    meta = {
        "prompt": args.prompt, "fps": int(args.fps), "resize": int(args.resize),
        "base_cam": args.base_cam, "wrist_cam": args.wrist_cam,
        "state_udp": args.state_udp, "action_udp": (args.action_udp or None),
    }
    (ep_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    steps_f = open(ep_dir / "steps.jsonl", "w", encoding="utf-8")

    base_stream = MjpegStream(args.base_cam) if args.base_cam else None
    wrist_stream = MjpegStream(args.wrist_cam) if args.wrist_cam else None
    state_sock = _start_udp_listener(args.state_udp)
    action_sock = _start_udp_listener(args.action_udp or None)

    def _prep(img: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if img is None: return None
        if img.shape[0] != args.resize or img.shape[1] != args.resize:
            img = cv2.resize(img, (args.resize, args.resize), interpolation=cv2.INTER_AREA)
        return img

    period = 1.0 / max(1, int(args.fps)); step = 0
    print(f"Recording to {ep_dir} (Ctrl+C to stop)")
    try:
        while True:
            t0 = time.time(); ts = time.time()
            ok_b, base_img = (base_stream.read() if base_stream else (False, None))
            ok_w, wrist_img = (wrist_stream.read() if wrist_stream else (False, None))
            base_img = _prep(base_img) if ok_b else None
            wrist_img = _prep(wrist_img) if ok_w else None

            state_msg = _recv_latest_json(state_sock)
            action_msg = _recv_latest_json(action_sock)

            base_fn = wrist_fn = None
            if base_img is not None:
                base_fn = f"{step:06d}.jpg"
                cv2.imwrite(str(img_base_dir / base_fn), cv2.cvtColor(base_img, cv2.COLOR_RGB2BGR))
            if wrist_img is not None:
                wrist_fn = f"{step:06d}.jpg"
                cv2.imwrite(str(img_wrist_dir / wrist_fn), cv2.cvtColor(wrist_img, cv2.COLOR_RGB2BGR))

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
        for s in (base_stream, wrist_stream):
            try: s and s.close()
            except Exception: pass
        for sk in (state_sock, action_sock):
            try: sk and sk.close()
            except Exception: pass


if __name__ == "__main__":
    main()


