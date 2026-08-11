"""
Minimal thread-safe TTL cache.

Used for both price history and news sentiment. Both are slow network calls whose
results are stable for minutes-to-hours, and both are hit from FastAPI's worker
threadpool, so entries must be safe to touch concurrently.

Deliberately in-process: there is no Redis in this stack yet, and a dict behind a
lock covers the single-container demo case. Note that prod runs uvicorn with
--workers 2, so each worker keeps its OWN cache — a cached entry in one worker is
invisible to the other. That only costs a duplicate fetch, never correctness.
"""

import threading
import time


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        """Return the cached value, or None if absent or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            # Expire on read rather than with a sweeper thread; the key space is
            # bounded by the ticker registry, so stale entries cannot pile up.
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self.ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
