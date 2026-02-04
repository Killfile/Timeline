"""Simple per-IP rate limiter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RateLimitWindow:
    window_start: datetime
    count: int


class RateLimiter:
    """Fixed-window rate limiter with burst support."""

    def __init__(self, limit_per_minute: int, burst: int) -> None:
        self._limit = limit_per_minute
        self._burst = burst
        self._window_seconds = 60
        self._entries: dict[str, RateLimitWindow] = {}
        self._lock = Lock()
        self._last_cleanup: datetime = _utcnow()
        self._cleanup_interval_seconds = 300  # Clean up every 5 minutes

    def _cleanup_expired_entries(self, now: datetime) -> None:
        """Remove entries older than the rate limit window.
        
        Should be called while holding self._lock.
        """
        cutoff = now - timedelta(seconds=self._window_seconds)
        expired_keys = [
            key for key, window in self._entries.items()
            if (now - window.window_start).total_seconds() >= self._window_seconds
        ]
        for key in expired_keys:
            del self._entries[key]

    def allow(self, key: str, now: datetime | None = None) -> bool:
        if now is None:
            now = _utcnow()
        with self._lock:
            # Periodic cleanup to prevent unbounded memory growth
            if (now - self._last_cleanup).total_seconds() >= self._cleanup_interval_seconds:
                self._cleanup_expired_entries(now)
                self._last_cleanup = now
            
            window = self._entries.get(key)
            if window is None or (now - window.window_start).total_seconds() >= self._window_seconds:
                self._entries[key] = RateLimitWindow(window_start=now, count=1)
                return True

            if window.count < self._limit + self._burst:
                window.count += 1
                return True

            return False
