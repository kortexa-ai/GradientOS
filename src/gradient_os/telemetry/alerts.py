import threading
import time
from collections import deque
from typing import Deque, Dict, List, Optional, TypedDict


class Alert(TypedDict, total=False):
	# Severity level of the alert
	level: str  # "error" | "warning" | "info"
	# Machine-friendly code/kind for filtering/analytics
	kind: str
	# Human-readable message
	message: str
	# Optional related servo IDs
	servo_ids: List[int]
	# Event timestamp (seconds since epoch)
	ts: float
	# Arbitrary structured details (kept small)
	details: dict


_lock = threading.Lock()
_queue: Deque[Alert] = deque(maxlen=200)

# Simple duplicate suppression window per key
_last_emit_by_key: Dict[str, float] = {}
_dedupe_window_s = 2.0


def _now() -> float:
	return time.time()


def names_for_status_bits(value: int) -> List[str]:
	"""Translate a status/error byte (bitfield) into human-readable names."""
	labels = {
		0: "Overload",
		1: "Overheat",
		2: "Overvoltage",
		3: "Undervoltage",
		4: "Stall",
		5: "Position Fault",
		6: "Comm/Error",
		7: "Unknown",
	}
	return [labels.get(i, f"b{i}") for i in range(8) if ((value >> i) & 1) == 1]


def push_alert(
	level: str,
	kind: str,
	message: str,
	servo_ids: Optional[List[int]] = None,
	details: Optional[dict] = None,
	key: Optional[str] = None,
) -> None:
	"""
	Push an alert into the ring buffer with lightweight duplicate suppression.
	- level: "error" | "warning" | "info"
	- kind: machine-friendly code like "SYNCREAD_TIMEOUT" or "SERVO_STATUS"
	- message: human-readable message
	- key: if provided, used for de-duplication; defaults to message+kind
	"""
	global _last_emit_by_key
	now_ts = _now()
	dedupe_key = key or f"{kind}:{message}"
	with _lock:
		last = _last_emit_by_key.get(dedupe_key)
		if last is not None and (now_ts - last) < _dedupe_window_s:
			return
		_last_emit_by_key[dedupe_key] = now_ts
		_queue.append(
			Alert(
				level=level,
				kind=kind,
				message=message,
				servo_ids=list(servo_ids) if servo_ids else [],
				ts=now_ts,
				details=details or {},
			)
		)


def drain_alerts(max_items: int = 50) -> List[Alert]:
	"""Atomically drain up to max_items alerts from the buffer."""
	items: List[Alert] = []
	with _lock:
		for _ in range(min(max_items, len(_queue))):
			items.append(_queue.popleft())
	return items


