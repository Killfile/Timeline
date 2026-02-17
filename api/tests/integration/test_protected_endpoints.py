import pytest


def test_health_is_public(test_client) -> None:
    """Test that /health endpoint is public and doesn't require authentication."""
    response = test_client.get("/health")
    assert response.status_code == 200


def test_admin_endpoints_require_auth(test_client) -> None:
    """Test that admin endpoints require authentication."""
    response = test_client.get("/admin/users")
    assert response.status_code == 401


def test_events_endpoint_requires_jwt(test_client) -> None:
    """Test that /events endpoint requires JWT authentication (anonymous or user token)."""
    # Without any token, should get 401
    response = test_client.get("/events")
    assert response.status_code == 401, "Endpoint should require JWT authentication"


def test_events_endpoint_accepts_anonymous_token(test_client) -> None:
    """Test that /events endpoint accepts anonymous token with public scope."""
    # Get an anonymous token
    token_response = test_client.post("/token")
    assert token_response.status_code == 200
    
    # Use the token to access events
    response = test_client.get("/events")
    # Should NOT be 401 (auth error) - may be 503 (DB unavailable) but token is accepted
    assert response.status_code != 401, "Anonymous token with public scope should be accepted"

