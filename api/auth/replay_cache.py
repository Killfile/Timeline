"""In-memory replay cache for JWT jti values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ReplayCacheEntry:
    expires_at: datetime


class ReplayCache:
    """Tracks token IDs (jti) to prevent replay within a TTL window."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, ReplayCacheEntry] = {}
        self._lock = Lock()

    def _prune(self, now: datetime) -> None:
        expired_keys = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired_keys:
            self._entries.pop(key, None)

    def is_replay(self, token_id: str, now: datetime | None = None) -> bool:
        if now is None:
            now = _utcnow()
        with self._lock:
            self._prune(now)
            return token_id in self._entries

    def mark_seen(self, token_id: str, now: datetime | None = None) -> None:
        if now is None:
            now = _utcnow()
        expires_at = now + timedelta(seconds=self._ttl_seconds)
        with self._lock:
            self._entries[token_id] = ReplayCacheEntry(expires_at=expires_at)

    def check_and_mark(self, token_id: str, now: datetime | None = None) -> bool:
        """Returns True if token_id is a replay, False otherwise.

        If not a replay, the token_id is marked as seen.
        """
        if now is None:
            now = _utcnow()
        with self._lock:
            self._prune(now)
            if token_id in self._entries:
                return True
            self._entries[token_id] = ReplayCacheEntry(
                expires_at=now + timedelta(seconds=self._ttl_seconds)
            )
            return False
