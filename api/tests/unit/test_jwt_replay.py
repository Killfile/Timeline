"""
Unit tests for JWT expiration enforcement.

Tests token expiration behavior to ensure tokens are rejected after TTL expires.
Note: We've implemented token reusability within TTL (standard JWT behavior).
Replay protection comes from short TTL + signature validation + expiration checking.
"""

import time
from datetime import datetime, timedelta, timezone
import pytest

from auth.config import AuthConfig
from auth.jwt_service import generate_token, decode_token
import jwt


def _build_test_config(ttl_seconds=900):
    """Helper to build AuthConfig with cookie fields."""
    return AuthConfig(
        client_secret="test-secret",  # Obsolete but kept for backwards compat
        jwt_secret="jwt-secret",
        jwt_issuer="timeline-api",
        jwt_audience="timeline-frontend",
        allowed_origins=("http://localhost",),  # Obsolete but kept for backwards compat
        token_ttl_seconds=ttl_seconds,
        replay_window_seconds=900,
        rate_limit_per_minute=60,
        rate_limit_burst=10,
        cookie_name="test_auth",
        cookie_secure=False,
        cookie_samesite="Lax",
        cookie_domain=None,
    )


def test_token_expires_after_ttl():
    """Test that tokens are rejected after their TTL expires."""
    config = _build_test_config(ttl_seconds=1)
    
    # Generate a token
    token_payload = generate_token(config)
    
    # Token should be valid immediately
    claims = decode_token(token_payload.token, config)
    assert claims["iss"] == "timeline-api"
    assert claims["aud"] == "timeline-frontend"
    assert "jti" in claims
    assert "iat" in claims
    assert "exp" in claims
    
    # Wait for token to expire
    time.sleep(2)
    
    # Token should now be rejected
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token_payload.token, config)


def test_token_reusable_within_ttl():
    """Test that tokens can be used multiple times within their TTL."""
    config = _build_test_config(ttl_seconds=10)
    
    # Generate a token
    token_payload = generate_token(config)
    
    # Use token multiple times - should succeed
    for i in range(5):
        claims = decode_token(token_payload.token, config)
        assert claims["iss"] == "timeline-api"
        assert "jti" in claims
        time.sleep(0.1)


def test_token_requires_expiration_claim():
    """Test that tokens without exp claim are rejected."""
    config = _build_test_config(ttl_seconds=900)
    
    # Create a token without exp claim
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "timeline-api",
        "aud": "timeline-frontend",
        "iat": int(now.timestamp()),
        "jti": "test-jti"
        # Missing exp claim
    }
    
    token = jwt.encode(claims, config.jwt_secret, algorithm="HS256")
    
    # Token should be rejected
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, config)


def test_token_requires_issued_at_claim():
    """Test that tokens without iat claim are rejected."""
    config = _build_test_config(ttl_seconds=900)
    
    # Create a token without iat claim
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "timeline-api",
        "aud": "timeline-frontend",
        "exp": int((now + timedelta(seconds=900)).timestamp()),
        "jti": "test-jti"
        # Missing iat claim
    }
    
    token = jwt.encode(claims, config.jwt_secret, algorithm="HS256")
    
    # Token should be rejected
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, config)


def test_token_requires_jti_claim():
    """Test that tokens without jti claim are rejected."""
    config = _build_test_config(ttl_seconds=900)
    
    # Create a token without jti claim
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "timeline-api",
        "aud": "timeline-frontend",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=900)).timestamp())
        # Missing jti claim
    }
    
    token = jwt.encode(claims, config.jwt_secret, algorithm="HS256")
    
    # Token should be rejected
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, config)


def test_expired_token_includes_exp_in_error():
    """Test that expired token errors include expiration information."""
    config = _build_test_config(ttl_seconds=1)
    
    # Generate and let token expire
    token_payload = generate_token(config)
    time.sleep(2)
    
    # Verify the error is specifically about expiration
    try:
        decode_token(token_payload.token, config)
        assert False, "Should have raised ExpiredSignatureError"
    except jwt.ExpiredSignatureError as e:
        # PyJWT raises ExpiredSignatureError for expired tokens
        assert "Signature has expired" in str(e)
