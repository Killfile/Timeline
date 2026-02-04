from datetime import timedelta

import jwt
import pytest

from api.auth.config import AuthConfig
from api.auth.jwt_service import decode_token, generate_token


def _build_config() -> AuthConfig:
    return AuthConfig(
        client_secret="client-secret",  # Obsolete but kept for backwards compat
        jwt_secret="jwt-secret",
        jwt_issuer=None,
        jwt_audience=None,
        allowed_origins=("http://localhost:3000",),  # Obsolete but kept for backwards compat
        token_ttl_seconds=60,
        replay_window_seconds=60,
        rate_limit_per_minute=60,
        rate_limit_burst=10,
        cookie_name="test_auth",
        cookie_secure=False,
        cookie_samesite="Lax",
        cookie_domain=None,
    )


def test_generate_and_decode_token_round_trip() -> None:
    config = _build_config()
    payload = generate_token(config)

    assert payload.token
    assert payload.expires_in == 60

    claims = decode_token(payload.token, config)
    assert "iat" in claims
    assert "exp" in claims
    assert "jti" in claims


def test_decode_token_requires_jti() -> None:
    config = _build_config()
    claims = {"iat": 1, "exp": 2}
    token = jwt.encode(claims, config.jwt_secret, algorithm="HS256")

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_token(token, config)
