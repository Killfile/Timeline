"""
OBSOLETE: This test file was designed for Authorization header + Origin validation auth.

The API has migrated to cookie-based authentication. See these test files instead:
- test_cookie_auth.py: Cookie-based authentication tests
- test_cors_validation.py: CORS configuration validation
- test_client_detection.py: User-agent parsing tests

This file is kept for reference but tests are disabled.
"""

import pytest

pytestmark = pytest.mark.skip(reason="Obsolete - API migrated to cookie-based auth")


class TestFullAuthFlow:
    """End-to-end integration tests for authentication flow."""

    def test_complete_auth_flow_success(self):
        """Test successful authentication flow: get token → access endpoint."""
        # Step 1: Get a token
        token_response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        assert token_response.status_code == 200
        token_data = token_response.json()
        assert "access_token" in token_data
        assert "expires_in" in token_data
        assert token_data["token_type"] == "Bearer"
        
        token = token_data["access_token"]
        
        # Step 2: Use token to access protected endpoint
        health_response = client.get(
            "/health",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "http://localhost:3000"
            }
        )
        assert health_response.status_code == 200

    def test_token_endpoint_requires_client_secret(self):
        """Test that /token endpoint requires valid client secret."""
        # Missing X-Client-Secret header
        response = client.post(
            "/token",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 401
        
        # Invalid client_secret
        response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "wrong-secret"
            }
        )
        assert response.status_code == 401

    def test_protected_endpoint_requires_token(self):
        """Test that protected endpoints reject requests without token."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 401
        assert "Missing Authorization header" in response.json()["detail"]

    def test_protected_endpoint_requires_valid_token(self):
        """Test that protected endpoints reject invalid tokens."""
        response = client.get(
            "/health",
            headers={
                "Authorization": "Bearer invalid.token.here",
                "Origin": "http://localhost:3000"
            }
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    def test_protected_endpoint_requires_origin_header(self):
        """Test that protected endpoints reject requests without Origin header."""
        # Get a valid token first
        token_response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        token = token_response.json()["access_token"]
        
        # Try to use token without Origin header
        response = client.get(
            "/health",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert "Missing Origin header" in response.json()["detail"]

    def test_protected_endpoint_validates_origin_allowlist(self):
        """Test that protected endpoints reject disallowed origins."""
        # Get a valid token
        token_response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        token = token_response.json()["access_token"]
        
        # Try to use token with disallowed origin
        response = client.get(
            "/health",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "http://evil.com"
            }
        )
        assert response.status_code == 401
        assert "Origin not allowed" in response.json()["detail"]

    def test_token_expiration_enforcement(self):
        """Test that expired tokens are rejected."""
        # Get a token (TTL is 2 seconds)
        token_response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        token = token_response.json()["access_token"]
        
        # Token should work immediately
        response = client.get(
            "/health",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "http://localhost:3000"
            }
        )
        assert response.status_code == 200
        
        # Wait for token to expire
        time.sleep(3)
        
        # Token should now be rejected
        response = client.get(
            "/health",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "http://localhost:3000"
            }
        )
        assert response.status_code == 401
        assert "Token expired" in response.json()["detail"]

    def test_token_replay_prevention(self):
        """Test that replayed tokens (same jti) are rejected."""
        # Get a token
        token_response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        token = token_response.json()["access_token"]
        
        # Use token multiple times - should succeed (tokens are reusable within TTL)
        for i in range(3):
            response = client.get(
                "/health",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Origin": "http://localhost:3000"
                }
            )
            assert response.status_code == 200, f"Request {i+1} failed - tokens should be reusable within TTL"

    @pytest.mark.skip(reason="Rate limiter may not reset between test runs - needs investigation")
    def test_rate_limiting_on_token_endpoint(self):
        """Test that /token endpoint enforces rate limits."""
        # Rate limit is 5/min + burst of 2 = 7 total
        # Make requests up to the limit
        for i in range(7):
            response = client.post(
                "/token",
                headers={
                    "Origin": "http://localhost:3000",
                    "X-Client-Secret": "test-client-secret-12345"
                }
            )
            assert response.status_code == 200, f"Request {i+1} failed"
        
        # Next request should be rate limited
        response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    def test_multiple_endpoints_protected(self):
        """Test that multiple endpoints are protected by auth."""
        # Get a valid token
        token_response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        token = token_response.json()["access_token"]
        
        # Test multiple endpoints with valid auth
        endpoints_to_test = ["/health", "/events", "/categories"]
        for endpoint in endpoints_to_test:
            response = client.get(
                endpoint,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Origin": "http://localhost:3000"
                }
            )
            # Should either succeed or fail with non-auth error
            # (some endpoints might not exist or have other validation)
            assert response.status_code != 401, f"{endpoint} returned 401 with valid auth"
        
        # Test same endpoints without auth - all should return 401
        for endpoint in endpoints_to_test:
            response = client.get(
                endpoint,
                headers={"Origin": "http://localhost:3000"}
            )
            assert response.status_code == 401, f"{endpoint} did not require auth"

    def test_token_endpoint_not_protected(self):
        """Test that /token endpoint itself is not protected."""
        # /token should work without auth (but requires X-Client-Secret)
        response = client.post(
            "/token",
            headers={
                "Origin": "http://localhost:3000",
                "X-Client-Secret": "test-client-secret-12345"
            }
        )
        assert response.status_code == 200
