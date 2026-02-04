import pytest


def test_health_requires_auth(test_client) -> None:
    """Test that /health endpoint requires authentication."""
    response = test_client.get("/health")
    assert response.status_code == 401
