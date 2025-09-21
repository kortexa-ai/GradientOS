import threading
from typing import Optional, Tuple
import requests
import numpy as np
import cv2


class MjpegStream:
    def __init__(self, url: str, *, timeout: float = 5.0) -> None:
        self._url = url
        self._timeout = timeout
        self._session = requests.Session()
        self._stop = False
        self._last: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self) -> None:
        try:
            with self._session.get(self._url, stream=True, timeout=self._timeout) as r:
                r.raise_for_status()
                buf = bytearray()
                for chunk in r.iter_content(chunk_size=4096):
                    if self._stop:
                        break
                    if not chunk:
                        continue
                    buf.extend(chunk)
                    while True:
                        s = buf.find(b"\xff\xd8"); e = buf.find(b"\xff\xd9")
                        if s != -1 and e != -1 and e > s:
                            jpeg = bytes(buf[s:e+2]); del buf[:e+2]
                            arr = np.frombuffer(jpeg, dtype=np.uint8)
                            bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                            if bgr is not None:
                                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                                with self._lock:
                                    self._last = rgb
                        else:
                            break
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


