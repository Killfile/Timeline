import os
import pytest

from api.auth.config import load_auth_config


def test_load_auth_config_requires_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("API_JWT_SECRET", raising=False)
    with pytest.raises(ValueError):
        load_auth_config()


def test_load_auth_config_parses_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("API_ALLOWED_ORIGINS", "http://localhost:3000, https://example.com/")
    monkeypatch.setenv("API_TOKEN_TTL_SECONDS", "120")
    monkeypatch.setenv("API_TOKEN_REPLAY_WINDOW_SECONDS", "300")
    monkeypatch.setenv("API_TOKEN_RATE_LIMIT_PER_MIN", "10")
    monkeypatch.setenv("API_TOKEN_RATE_LIMIT_BURST", "2")

    config = load_auth_config()

    assert config.client_secret == "client-secret"
    assert config.jwt_secret == "jwt-secret"
    assert config.allowed_origins == ("http://localhost:3000", "https://example.com/")
    assert config.token_ttl_seconds == 120
    assert config.replay_window_seconds == 300
    assert config.rate_limit_per_minute == 10
    assert config.rate_limit_burst == 2

def test_load_auth_config_cookie_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that cookie configuration has sensible defaults."""
    monkeypatch.setenv("API_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")
    # Remove test env vars set by conftest.py
    monkeypatch.delenv("API_COOKIE_NAME", raising=False)
    monkeypatch.delenv("API_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("API_COOKIE_SAMESITE", raising=False)

    config = load_auth_config()

    assert config.cookie_name == "timeline_auth"
    assert config.cookie_secure is True
    assert config.cookie_samesite == "strict"
    assert config.cookie_domain is None


def test_load_auth_config_cookie_custom_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that cookie configuration can be customized via environment."""
    monkeypatch.setenv("API_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("API_COOKIE_NAME", "my_custom_cookie")
    monkeypatch.setenv("API_COOKIE_SECURE", "false")
    monkeypatch.setenv("API_COOKIE_SAMESITE", "lax")
    monkeypatch.setenv("API_COOKIE_DOMAIN", ".example.com")

    config = load_auth_config()

    assert config.cookie_name == "my_custom_cookie"
    assert config.cookie_secure is False
    assert config.cookie_samesite == "lax"
    assert config.cookie_domain == ".example.com"


def test_load_auth_config_cookie_samesite_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that invalid cookie_samesite values fall back to default."""
    monkeypatch.setenv("API_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("API_COOKIE_SAMESITE", "invalid_value")

    config = load_auth_config()

    assert config.cookie_samesite == "strict"  # Falls back to default


def test_load_auth_config_cookie_secure_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test various ways to specify cookie_secure boolean."""
    monkeypatch.setenv("API_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("API_JWT_SECRET", "jwt-secret")

    # Test "true"
    monkeypatch.setenv("API_COOKIE_SECURE", "true")
    config = load_auth_config()
    assert config.cookie_secure is True

    # Test "1"
    monkeypatch.setenv("API_COOKIE_SECURE", "1")
    config = load_auth_config()
    assert config.cookie_secure is True

    # Test "yes"
    monkeypatch.setenv("API_COOKIE_SECURE", "yes")
    config = load_auth_config()
    assert config.cookie_secure is True

    # Test "false"
    monkeypatch.setenv("API_COOKIE_SECURE", "false")
    config = load_auth_config()
    assert config.cookie_secure is False