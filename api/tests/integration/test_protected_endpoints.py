from fastapi.testclient import TestClient

from api.api import app


client = TestClient(app)


def test_health_requires_auth() -> None:
    import os
    os.environ["API_CLIENT_SECRET"] = "client-secret"
    os.environ["API_JWT_SECRET"] = "jwt-secret"
    os.environ["API_ALLOWED_ORIGINS"] = "http://localhost:3000"
    response = client.get("/health")
    assert response.status_code == 401
