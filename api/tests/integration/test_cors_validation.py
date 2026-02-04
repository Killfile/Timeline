"""CORS Configuration Validation Tests

Tests that CORS is properly configured for cookie-based authentication.
"""

import pytest
from fastapi.testclient import TestClient


def test_cors_preflight_token_endpoint(test_client: TestClient) -> None:
    """Test CORS preflight (OPTIONS) request for /token endpoint."""
    response = test_client.options(
        "/token",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_preflight_events_endpoint(test_client: TestClient) -> None:
    """Test CORS preflight (OPTIONS) request for /events endpoint."""
    response = test_client.options(
        "/events",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_cors_actual_request_with_credentials(test_client: TestClient) -> None:
    """Test actual request with Origin header returns CORS headers."""
    # First get a token
    token_response = test_client.post(
        "/token",
        headers={"Origin": "http://localhost:3000"},
    )
    assert token_response.status_code == 200
    
    # Verify CORS headers on token response
    assert token_response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert token_response.headers.get("access-control-allow-credentials") == "true"
    
    # Extract cookie
    cookies = token_response.cookies
    
    # Make authenticated request with cookie
    # Note: /events will return 503 if database is unavailable, but we're testing CORS
    events_response = test_client.get(
        "/events",
        headers={"Origin": "http://localhost:3000"},
        cookies=cookies,
    )
    
    # Verify CORS headers are present regardless of database status
    assert events_response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert events_response.headers.get("access-control-allow-credentials") == "true"
    
    # If database is available, should succeed; otherwise 503 is acceptable
    assert events_response.status_code in [200, 503]


def test_cors_rejects_unknown_origin(test_client: TestClient) -> None:
    """Test that requests from non-allowed origins are rejected."""
    response = test_client.options(
        "/token",
        headers={
            "Origin": "http://evil-site.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    
    # FastAPI CORS middleware returns 400 for disallowed origins
    assert response.status_code == 400


def test_cors_allows_localhost_variants(test_client: TestClient) -> None:
    """Test that both localhost and 127.0.0.1 are allowed."""
    # Test localhost
    response1 = test_client.post(
        "/token",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response1.status_code == 200
    assert response1.headers.get("access-control-allow-origin") == "http://localhost:3000"
    
    # Test 127.0.0.1
    response2 = test_client.post(
        "/token",
        headers={"Origin": "http://127.0.0.1:3000"},
    )
    assert response2.status_code == 200
    assert response2.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"


def test_cors_credentials_flag_always_set(test_client: TestClient) -> None:
    """Test that Access-Control-Allow-Credentials is always 'true'."""
    endpoints = ["/token", "/health", "/events", "/categories"]
    
    for endpoint in endpoints:
        # Try OPTIONS (preflight)
        preflight_response = test_client.options(
            endpoint,
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        
        # Preflight should set credentials flag
        if preflight_response.status_code == 200:
            assert preflight_response.headers.get("access-control-allow-credentials") == "true"


def test_cors_no_wildcard_origin(test_client: TestClient) -> None:
    """Test that wildcard origin (*) is NOT used (incompatible with credentials)."""
    response = test_client.post(
        "/token",
        headers={"Origin": "http://localhost:3000"},
    )
    
    # Should have specific origin, never "*"
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != "*"
    assert allow_origin == "http://localhost:3000"
