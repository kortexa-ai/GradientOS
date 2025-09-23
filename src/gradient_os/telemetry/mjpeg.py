import threading
from typing import Optional, Tuple
import requests
import numpy as np
import cv2


class MjpegStream:
    def __init__(self, url: str, *, timeout: float = 10.0) -> None:
        self._url = url
        self._timeout = timeout
        self._session = requests.Session()
        self._stop = False
        self._last: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        # Prefer OpenCV backend for HTTP MJPEG URLs (more tolerant to variations)
        try:
            is_http = isinstance(url, str) and url.startswith("http")
            use_cv2 = is_http and url.endswith(".mjpg")
        except Exception:
            use_cv2 = False
        self._backend = "cv2" if use_cv2 else "requests"
        target = self._reader_cv2 if self._backend == "cv2" else self._reader_requests
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def _reader_requests(self) -> None:
        backoff_s = 0.5
        while not self._stop:
            try:
                with self._session.get(self._url, stream=True, timeout=self._timeout) as r:
                    r.raise_for_status()
                    buf = bytearray()
                    for chunk in r.iter_content(chunk_size=8192):
                        if self._stop:
                            break
                        if not chunk:
                            continue
                        buf.extend(chunk)
                        while True:
                            s = buf.find(b"\xff\xd8"); e = buf.find(b"\xff\xd9")
                            if s == -1 or e == -1:
                                break
                            if e < s:
                                # Drop bytes up to first start to resync
                                del buf[:s]
                                continue
                            # e >= s
                            jpeg = bytes(buf[s:e+2]); del buf[:e+2]
                            arr = np.frombuffer(jpeg, dtype=np.uint8)
                            bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                            if bgr is not None:
                                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                                with self._lock:
                                    self._last = rgb
                        # Prevent unbounded growth in worst-case
                        if len(buf) > 4 * 1024 * 1024:
                            # Drop until last start marker if present
                            last_s = buf.rfind(b"\xff\xd8")
                            if last_s != -1:
                                del buf[:last_s]
                            else:
                                buf.clear()
                # If we exit context without stop, reset backoff
                backoff_s = 0.5
            except Exception:
                # Connection failed or timed out; retry with backoff
                if self._stop:
                    break
                try:
                    import time as _t
                    _t.sleep(backoff_s)
                except Exception:
                    pass
                # Exponential backoff capped
                backoff_s = min(backoff_s * 2.0, 5.0)

    def _reader_cv2(self) -> None:
        try:
            cap = cv2.VideoCapture(self._url)
        except Exception:
            cap = None
        if cap is None or not cap.isOpened():
            # Fallback to requests backend
            self._backend = "requests"
            self._reader_requests()
            return
        try:
            import time as _t
            while not self._stop:
                ok, bgr = cap.read()
                if not ok:
                    _t.sleep(0.01)
                    continue
                try:
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                except Exception:
                    rgb = bgr
                with self._lock:
                    self._last = rgb
        except Exception:
            pass
        finally:
            try:
                cap.release()
            except Exception:
                pass

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if self._last is None:
                return False, None
            return True, self._last.copy()

    def close(self) -> None:
        self._stop = True
        try: self._thread.join(timeout=1.0)
        except Exception: pass
        try: self._session.close()
        except Exception: pass


