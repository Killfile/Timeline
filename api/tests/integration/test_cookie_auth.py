"""Integration tests for cookie-based authentication."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api.api import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_env(monkeypatch):
    """Set up auth environment variables."""
    monkeypatch.setenv("API_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("API_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("API_ALLOWED_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("API_COOKIE_NAME", "test_auth_cookie")
    monkeypatch.setenv("API_COOKIE_SECURE", "false")  # For testing
    monkeypatch.setenv("API_COOKIE_SAMESITE", "lax")
    yield


class TestTokenEndpoint:
    """Tests for /token endpoint with cookie-based auth."""

    def test_token_sets_cookie(self, client, auth_env):
        """Test that /token endpoint sets cookie with correct attributes."""
        response = client.post("/token")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "expires_in" in response.json()
        
        # Check cookie is set
        assert "test_auth_cookie" in response.cookies
        
        # Check cookie attributes
        cookie = response.cookies["test_auth_cookie"]
        assert cookie  # Not empty
        assert response.headers.get("set-cookie")  # Cookie header present

    def test_token_cookie_httponly(self, client, auth_env):
        """Test that cookie has HttpOnly flag."""
        response = client.post("/token")
        
        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header
        assert "HttpOnly" in set_cookie_header

    def test_token_cookie_samesite(self, client, auth_env):
        """Test that cookie has SameSite attribute."""
        response = client.post("/token")
        
        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header
        assert "SameSite=lax" in set_cookie_header or "SameSite=Lax" in set_cookie_header

    def test_token_rate_limiting(self, client, auth_env, monkeypatch):
        """Test that rate limiting is enforced."""
        # Set very low rate limit
        monkeypatch.setenv("API_TOKEN_RATE_LIMIT_PER_MIN", "2")
        monkeypatch.setenv("API_TOKEN_RATE_LIMIT_BURST", "1")
        
        # Reload config by forcing module reload
        from api.auth import config
        import importlib
        importlib.reload(config)
        
        # First request should succeed
        response1 = client.post("/token")
        assert response1.status_code == 200
        
        # Second request should succeed (burst)
        response2 = client.post("/token")
        assert response2.status_code == 200
        
        # Third request should be rate limited
        response3 = client.post("/token")
        assert response3.status_code == 429
        assert "rate limit" in response3.json()["detail"].lower()


class TestProtectedEndpoints:
    """Tests for protected endpoints with cookie authentication."""

    def test_missing_cookie_returns_401(self, client, auth_env):
        """Test that missing cookie returns 401."""
        response = client.get("/events")
        
        assert response.status_code == 401
        assert "cookie" in response.json()["detail"].lower()

    def test_valid_cookie_authenticates(self, client, auth_env):
        """Test that valid cookie allows access to protected endpoints."""
        # Get a token
        token_response = client.post("/token")
        assert token_response.status_code == 200
        cookie_value = token_response.cookies["test_auth_cookie"]
        
        # Use cookie to access protected endpoint
        response = client.get("/events", cookies={"test_auth_cookie": cookie_value})
        
        # Should not be 401 (actual response depends on endpoint implementation)
        assert response.status_code != 401

    def test_invalid_cookie_returns_401(self, client, auth_env):
        """Test that invalid cookie returns 401."""
        response = client.get("/events", cookies={"test_auth_cookie": "invalid-token"})
        
        assert response.status_code == 401

    def test_expired_cookie_returns_401(self, client, auth_env, monkeypatch):
        """Test that expired cookie returns 401."""
        # Set very short TTL
        monkeypatch.setenv("API_TOKEN_TTL_SECONDS", "1")
        
        # Reload config
        from api.auth import config
        import importlib
        importlib.reload(config)
        
        # Get a token
        token_response = client.post("/token")
        cookie_value = token_response.cookies["test_auth_cookie"]
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Try to use expired cookie
        response = client.get("/events", cookies={"test_auth_cookie": cookie_value})
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


class TestLogoutEndpoint:
    """Tests for /logout endpoint."""

    def test_logout_clears_cookie(self, client, auth_env):
        """Test that /logout clears the authentication cookie."""
        # First get a token
        token_response = client.post("/token")
        assert token_response.status_code == 200
        
        # Logout
        logout_response = client.post("/logout")
        
        assert logout_response.status_code == 200
        assert logout_response.json()["status"] == "success"
        
        # Check cookie is cleared (max_age=0)
        set_cookie_header = logout_response.headers.get("set-cookie")
        assert set_cookie_header
        assert "Max-Age=0" in set_cookie_header or "max-age=0" in set_cookie_header

    def test_logout_without_cookie(self, client, auth_env):
        """Test that logout works even without existing cookie."""
        response = client.post("/logout")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"


class TestCookieFlags:
    """Tests for cookie security flags."""

    def test_cookie_secure_flag_in_production(self, client, monkeypatch):
        """Test that Secure flag is set in production mode."""
        monkeypatch.setenv("API_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("API_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("API_COOKIE_SECURE", "true")
        
        response = client.post("/token")
        
        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header
        assert "Secure" in set_cookie_header

    def test_cookie_strict_samesite(self, client, monkeypatch):
        """Test that SameSite=Strict can be configured."""
        monkeypatch.setenv("API_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("API_JWT_SECRET", "test-jwt-secret")
        monkeypatch.setenv("API_COOKIE_SAMESITE", "strict")
        
        response = client.post("/token")
        
        set_cookie_header = response.headers.get("set-cookie")
        assert set_cookie_header
        assert "SameSite=strict" in set_cookie_header or "SameSite=Strict" in set_cookie_header
