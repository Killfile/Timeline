from datetime import datetime, timedelta, timezone

from api.auth.rate_limiter import RateLimiter


def test_rate_limiter_enforces_limit_and_burst() -> None:
    limiter = RateLimiter(limit_per_minute=2, burst=1)
    now = datetime.now(timezone.utc)

    assert limiter.allow("ip", now=now) is True
    assert limiter.allow("ip", now=now) is True
    assert limiter.allow("ip", now=now) is True
    assert limiter.allow("ip", now=now) is False

    later = now + timedelta(seconds=61)
    assert limiter.allow("ip", now=later) is True
