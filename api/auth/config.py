"""Configuration loading for API JWT protection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence


_DEFAULT_TOKEN_TTL_SECONDS = 900
_DEFAULT_REPLAY_WINDOW_SECONDS = 900
_DEFAULT_RATE_LIMIT_PER_MIN = 60
_DEFAULT_RATE_LIMIT_BURST = 10
_DEFAULT_COOKIE_NAME = "timeline_auth"
_DEFAULT_COOKIE_SAMESITE = "strict"
_DEFAULT_COOKIE_SECURE = True


@dataclass(frozen=True)
class AuthConfig:
    client_secret: str
    jwt_secret: str
    jwt_issuer: str | None
    jwt_audience: str | None
    allowed_origins: tuple[str, ...]
    token_ttl_seconds: int
    replay_window_seconds: int
    rate_limit_per_minute: int
    rate_limit_burst: int
    cookie_name: str
    cookie_secure: bool
    cookie_samesite: str
    cookie_domain: str | None


def _parse_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    return int(value)


def _parse_origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


def load_auth_config() -> AuthConfig:
    """Load auth configuration from environment variables."""
    client_secret = os.getenv("API_CLIENT_SECRET", "").strip()
    jwt_secret = os.getenv("API_JWT_SECRET", "").strip()

    if not client_secret:
        raise ValueError("API_CLIENT_SECRET must be set")
    if not jwt_secret:
        raise ValueError("API_JWT_SECRET must be set")

    allowed_origins = _parse_origins(os.getenv("API_ALLOWED_ORIGINS"))

    # Cookie configuration
    cookie_name = os.getenv("API_COOKIE_NAME", _DEFAULT_COOKIE_NAME).strip()
    cookie_secure_str = os.getenv("API_COOKIE_SECURE", str(_DEFAULT_COOKIE_SECURE)).strip().lower()
    cookie_secure = cookie_secure_str in ("true", "1", "yes")
    cookie_samesite = os.getenv("API_COOKIE_SAMESITE", _DEFAULT_COOKIE_SAMESITE).strip().lower()
    if cookie_samesite not in ("strict", "lax", "none"):
        cookie_samesite = _DEFAULT_COOKIE_SAMESITE
    cookie_domain = os.getenv("API_COOKIE_DOMAIN", "").strip() or None

    return AuthConfig(
        client_secret=client_secret,
        jwt_secret=jwt_secret,
        jwt_issuer=os.getenv("API_JWT_ISSUER") or None,
        jwt_audience=os.getenv("API_JWT_AUDIENCE") or None,
        allowed_origins=allowed_origins,
        token_ttl_seconds=_parse_int(os.getenv("API_TOKEN_TTL_SECONDS"), _DEFAULT_TOKEN_TTL_SECONDS),
        replay_window_seconds=_parse_int(
            os.getenv("API_TOKEN_REPLAY_WINDOW_SECONDS"),
            _DEFAULT_REPLAY_WINDOW_SECONDS,
        ),
        rate_limit_per_minute=_parse_int(
            os.getenv("API_TOKEN_RATE_LIMIT_PER_MIN"),
            _DEFAULT_RATE_LIMIT_PER_MIN,
        ),
        rate_limit_burst=_parse_int(
            os.getenv("API_TOKEN_RATE_LIMIT_BURST"),
            _DEFAULT_RATE_LIMIT_BURST,
        ),
        cookie_name=cookie_name,
        cookie_secure=cookie_secure,
        cookie_samesite=cookie_samesite,
        cookie_domain=cookie_domain,
    )


def normalize_origin(origin: str) -> str:
    return origin.rstrip("/")


def is_origin_allowed(origin: str, allowed: Sequence[str]) -> bool:
    if not allowed:
        return False
    normalized_origin = normalize_origin(origin)
    normalized_allowed = {normalize_origin(item) for item in allowed}
    return normalized_origin in normalized_allowed
