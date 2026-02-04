"""JWT encode/decode utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt

from .config import AuthConfig


@dataclass(frozen=True)
class TokenPayload:
    token: str
    expires_in: int
    issued_at: datetime
    token_id: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_token(config: AuthConfig) -> TokenPayload:
    issued_at = _utcnow()
    expires_at = issued_at + timedelta(seconds=config.token_ttl_seconds)
    token_id = str(uuid4())

    claims: dict[str, Any] = {
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": token_id,
    }

    if config.jwt_issuer:
        claims["iss"] = config.jwt_issuer
    if config.jwt_audience:
        claims["aud"] = config.jwt_audience

    token = jwt.encode(claims, config.jwt_secret, algorithm="HS256")
    return TokenPayload(
        token=token,
        expires_in=config.token_ttl_seconds,
        issued_at=issued_at,
        token_id=token_id,
    )


def decode_token(token: str, config: AuthConfig) -> dict[str, Any]:
    options = {
        "require": ["exp", "iat", "jti"],
    }
    return jwt.decode(
        token,
        config.jwt_secret,
        algorithms=["HS256"],
        audience=config.jwt_audience,
        issuer=config.jwt_issuer,
        options=options,
    )
