from datetime import datetime, timedelta, timezone

from api.auth.replay_cache import ReplayCache


def test_replay_cache_detects_replay() -> None:
    cache = ReplayCache(ttl_seconds=60)
    now = datetime.now(timezone.utc)

    assert cache.check_and_mark("token-1", now=now) is False
    assert cache.check_and_mark("token-1", now=now) is True


def test_replay_cache_prunes_expired() -> None:
    cache = ReplayCache(ttl_seconds=1)
    now = datetime.now(timezone.utc)

    cache.check_and_mark("token-1", now=now)
    later = now + timedelta(seconds=2)
    assert cache.check_and_mark("token-1", now=later) is False
