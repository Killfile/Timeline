"""Integration tests for admin authentication endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.api import app
from api.auth.config import load_auth_config
from api.auth.jwt_service import generate_token


@dataclass
class DummyConn:
    def close(self) -> None:
        return None


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_JWT_SECRET", "test-jwt-secret-67890")
    monkeypatch.setenv("COOKIE_NAME", "timeline_auth_test")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("COOKIE_SAMESITE", "lax")
    yield


def _mock_user(active: bool = True) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "email": "admin@example.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fake$hash",
        "is_active": active,
        "created_at": now,
        "updated_at": now,
    }


def test_admin_login_success_sets_cookie(client: TestClient, auth_env) -> None:
    with patch("api.api.get_db_connection", return_value=DummyConn()), \
        patch("api.api.fetch_user_by_email", return_value=_mock_user()), \
        patch("api.api.fetch_user_roles", return_value=["admin"]), \
        patch("api.api.verify_password", return_value=True):
        response = client.post(
            "/admin/login",
            json={"email": "admin@example.com", "password": "correct"},
        )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@example.com"
    assert "timeline_auth_test" in response.cookies


def test_admin_login_rejects_invalid_password(client: TestClient, auth_env) -> None:
    with patch("api.api.get_db_connection", return_value=DummyConn()), \
        patch("api.api.fetch_user_by_email", return_value=_mock_user()), \
        patch("api.api.fetch_user_roles", return_value=["admin"]), \
        patch("api.api.verify_password", return_value=False):
        response = client.post(
            "/admin/login",
            json={"email": "admin@example.com", "password": "wrong"},
        )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_admin_login_rejects_inactive_user(client: TestClient, auth_env) -> None:
    with patch("api.api.get_db_connection", return_value=DummyConn()), \
        patch("api.api.fetch_user_by_email", return_value=_mock_user(active=False)), \
        patch("api.api.fetch_user_roles", return_value=["admin"]), \
        patch("api.api.verify_password", return_value=True):
        response = client.post(
            "/admin/login",
            json={"email": "admin@example.com", "password": "correct"},
        )

    assert response.status_code == 401
    assert "inactive" in response.json()["detail"].lower()


def test_admin_me_requires_admin_role(client: TestClient, auth_env) -> None:
    config = load_auth_config()
    token_payload = generate_token(config, user_id="2", roles=["user"], scopes=[])
    client.cookies.set(config.cookie_name, token_payload.token)

    response = client.get("/admin/me")

    assert response.status_code == 403


def test_admin_me_returns_profile(client: TestClient, auth_env) -> None:
    config = load_auth_config()
    token_payload = generate_token(config, user_id="1", roles=["admin"], scopes=[])
    client.cookies.set(config.cookie_name, token_payload.token)

    with patch("api.api.get_db_connection", return_value=DummyConn()), \
        patch("api.api.fetch_user_by_id", return_value=_mock_user()), \
        patch("api.api.fetch_user_roles", return_value=["admin"]):
        response = client.get("/admin/me")

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"


def test_admin_logout_clears_cookie(client: TestClient, auth_env) -> None:
    config = load_auth_config()
    token_payload = generate_token(config, user_id="1", roles=["admin"], scopes=[])
    client.cookies.set(config.cookie_name, token_payload.token)

    response = client.post("/admin/logout")

    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie")
    assert set_cookie_header
    assert "max-age=0" in set_cookie_header.lower()
