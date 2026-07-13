"""A tiny thread-safe in-process TTL cache.

Used for live price/news responses (15 minutes, from config) and for
Narrative Lens replies (1 hour). No external cache infrastructure is
allowed by the spec, and none is needed at hackathon scale.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self._ttl = float(ttl_seconds)
        self._data: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            expires_at, value = hit
            if time.monotonic() > expires_at:
                del self._data[key]
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
