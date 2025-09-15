import socket
import threading
import queue
import select
import time
from typing import Optional, Tuple


class UdpClient:
    def __init__(self, target_ip: str, target_port: int):
        self.target_ip = target_ip
        self.target_port = target_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256 * 1024)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
        except Exception:
            pass

        self._incoming_queue: "queue.Queue[Tuple[bytes, Tuple[str, int]]]" = queue.Queue(maxsize=1000)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        try:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.2)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

    def send(self, text: str):
        self.sock.sendto(text.encode("utf-8"), (self.target_ip, self.target_port))

    def set_target(self, ip: str, port: Optional[int] = None):
        self.target_ip = ip
        if port is not None:
            self.target_port = port

    def try_receive_text(self, timeout_seconds: float = 0.0) -> Optional[str]:
        end_time = time.time() + max(0.0, timeout_seconds)
        while time.time() < end_time:
            try:
                data, _addr = self._incoming_queue.get_nowait()
                return data.decode("utf-8", errors="ignore").strip()
            except queue.Empty:
                time.sleep(0.005)
        try:
            data, _addr = self._incoming_queue.get_nowait()
            return data.decode("utf-8", errors="ignore").strip()
        except queue.Empty:
            return None

    def _receiver_loop(self):
        while self._running:
            try:
                rlist, _, _ = select.select([self.sock], [], [], 0.05)
                if not rlist:
                    continue
                data, addr = self.sock.recvfrom(4096)
                try:
                    self._incoming_queue.put_nowait((data, addr))
                except queue.Full:
                    try:
                        _ = self._incoming_queue.get_nowait()
                    except Exception:
                        pass
                    try:
                        self._incoming_queue.put_nowait((data, addr))
                    except Exception:
                        pass
            except Exception:
                time.sleep(0.01)


