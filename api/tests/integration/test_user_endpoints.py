"""Integration tests for user management endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestListUsers:
    """Tests for GET /admin/users endpoint."""

    def test_list_users_requires_auth(self, test_client):
        """Test that listing users requires authentication."""
        response = test_client.get("/admin/users")
        assert response.status_code == 401

    def test_list_users_requires_admin_role(self, test_client):
        """Test that listing users requires admin role."""
        # TODO: Create non-admin user and test 403
        pass

    def test_list_users_success(self, admin_client):
        """Test successful user listing."""
        response = admin_client.get("/admin/users")
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["users"], list)

    def test_list_users_with_limit_offset(self, admin_client):
        """Test user listing with pagination."""
        response = admin_client.get("/admin/users?limit=10&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    def test_list_users_with_email_filter(self, admin_client):
        """Test user listing with email filter."""
        response = admin_client.get("/admin/users?email_filter=admin")
        assert response.status_code == 200
        
        data = response.json()
        for user in data["users"]:
            assert "admin" in user["email"].lower()

    def test_list_users_with_role_filter(self, admin_client):
        """Test user listing with role filter."""
        response = admin_client.get("/admin/users?role_filter=admin")
        assert response.status_code == 200
        
        data = response.json()
        for user in data["users"]:
            assert "admin" in user["roles"]


class TestCreateUser:
    """Tests for POST /admin/users endpoint."""

    def test_create_user_requires_auth(self, test_client):
        """Test that creating users requires authentication."""
        response = test_client.post(
            "/admin/users",
            json={
                "email": "new@example.com",
                "password": "password123",
                "roles": ["user"],
            },
        )
        assert response.status_code == 401

    def test_create_user_success(self, admin_client):
        """Test successful user creation."""
        response = admin_client.post(
            "/admin/users",
            json={
                "email": "newuser@example.com",
                "password": "securePass123",
                "roles": ["user"],
            },
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "user" in data["roles"]
        assert data["is_active"] is True
        assert "id" in data

    def test_create_admin_user(self, admin_client):
        """Test creating admin user."""
        response = admin_client.post(
            "/admin/users",
            json={
                "email": "newadmin@example.com",
                "password": "adminPass123",
                "roles": ["admin"],
            },
        )
        assert response.status_code == 201
        
        data = response.json()
        assert "admin" in data["roles"]

    def test_create_user_duplicate_email(self, admin_client):
        """Test creating user with duplicate email."""
        # Create first user
        admin_client.post(
            "/admin/users",
            json={
                "email": "duplicate@example.com",
                "password": "password123",
                "roles": ["user"],
            },
        )
        
        # Try to create duplicate
        response = admin_client.post(
            "/admin/users",
            json={
                "email": "duplicate@example.com",
                "password": "password456",
                "roles": ["user"],
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_user_weak_password(self, admin_client):
        """Test creating user with weak password."""
        response = admin_client.post(
            "/admin/users",
            json={
                "email": "weak@example.com",
                "password": "short",
                "roles": ["user"],
            },
        )
        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]

    def test_create_user_invalid_email(self, admin_client):
        """Test creating user with invalid email."""
        response = admin_client.post(
            "/admin/users",
            json={
                "email": "not-an-email",
                "password": "password123",
                "roles": ["user"],
            },
        )
        assert response.status_code in (400, 422)

    def test_create_user_invalid_role(self, admin_client):
        """Test creating user with invalid role."""
        response = admin_client.post(
            "/admin/users",
            json={
                "email": "test@example.com",
                "password": "password123",
                "roles": ["invalid_role"],
            },
        )
        assert response.status_code == 400


class TestGetUser:
    """Tests for GET /admin/users/{user_id} endpoint."""

    def test_get_user_requires_auth(self, test_client):
        """Test that getting user requires authentication."""
        response = test_client.get("/admin/users/1")
        assert response.status_code == 401

    def test_get_user_success(self, admin_client):
        """Test successful user retrieval."""
        # Get the admin user (id=1)
        response = admin_client.get("/admin/users/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == 1
        assert "email" in data
        assert "roles" in data
        assert "is_active" in data

    def test_get_user_not_found(self, admin_client):
        """Test getting non-existent user."""
        response = admin_client.get("/admin/users/99999")
        assert response.status_code == 404


class TestUpdateUser:
    """Tests for PATCH /admin/users/{user_id} endpoint."""

    def test_update_user_requires_auth(self, test_client):
        """Test that updating user requires authentication."""
        response = test_client.patch(
            "/admin/users/1",
            json={"email": "new@example.com"},
        )
        assert response.status_code == 401

    def test_update_user_email(self, admin_client):
        """Test updating user email."""
        # Create a test user first
        create_response = admin_client.post(
            "/admin/users",
            json={
                "email": "update-test@example.com",
                "password": "password123",
                "roles": ["user"],
            },
        )
        user_id = create_response.json()["id"]
        
        # Update email
        response = admin_client.patch(
            f"/admin/users/{user_id}",
            json={"email": "updated@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_update_user_roles(self, admin_client):
        """Test updating user roles."""
        # Create a test user
        create_response = admin_client.post(
            "/admin/users",
            json={
                "email": "role-test@example.com",
                "password": "password123",
                "roles": ["user"],
            },
        )
        user_id = create_response.json()["id"]
        
        # Update to admin
        response = admin_client.patch(
            f"/admin/users/{user_id}",
            json={"roles": ["admin"]},
        )
        assert response.status_code == 200
        assert "admin" in response.json()["roles"]

    def test_update_user_deactivate(self, admin_client):
        """Test deactivating user."""
        # Create a test user
        create_response = admin_client.post(
            "/admin/users",
            json={
                "email": "deactivate-test@example.com",
                "password": "password123",
                "roles": ["user"],
            },
        )
        user_id = create_response.json()["id"]
        
        # Deactivate
        response = admin_client.patch(
            f"/admin/users/{user_id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_update_user_not_found(self, admin_client):
        """Test updating non-existent user."""
        response = admin_client.patch(
            "/admin/users/99999",
            json={"email": "new@example.com"},
        )
        assert response.status_code == 404


class TestDeleteUser:
    """Tests for DELETE /admin/users/{user_id} endpoint."""

    def test_delete_user_requires_auth(self, test_client):
        """Test that deleting user requires authentication."""
        response = test_client.delete("/admin/users/1")
        assert response.status_code == 401

    def test_delete_user_success(self, admin_client):
        """Test successful user deletion."""
        # Create a test user
        create_response = admin_client.post(
            "/admin/users",
            json={
                "email": "delete-test@example.com",
                "password": "password123",
                "roles": ["user"],
            },
        )
        user_id = create_response.json()["id"]
        
        # Delete
        response = admin_client.delete(f"/admin/users/{user_id}")
        assert response.status_code == 204
        
        # Verify user is deactivated (not deleted)
        get_response = admin_client.get(f"/admin/users/{user_id}")
        if get_response.status_code == 200:
            assert get_response.json()["is_active"] is False

    def test_delete_user_not_found(self, admin_client):
        """Test deleting non-existent user."""
        response = admin_client.delete("/admin/users/99999")
        assert response.status_code == 404


class TestChangeUserPassword:
    """Tests for POST /admin/users/{user_id}/password endpoint."""

    def test_change_password_requires_auth(self, test_client):
        """Test that changing password requires authentication."""
        response = test_client.post(
            "/admin/users/1/password",
            json={"new_password": "newPassword123"},
        )
        assert response.status_code == 401

    def test_change_password_success(self, admin_client):
        """Test successful password change."""
        # Create a test user
        create_response = admin_client.post(
            "/admin/users",
            json={
                "email": "password-test@example.com",
                "password": "oldPassword123",
                "roles": ["user"],
            },
        )
        user_id = create_response.json()["id"]
        
        # Change password
        response = admin_client.post(
            f"/admin/users/{user_id}/password",
            json={"new_password": "newPassword456"},
        )
        assert response.status_code == 200
        assert "success" in response.json()["message"].lower()

    def test_change_password_weak(self, admin_client):
        """Test changing to weak password."""
        response = admin_client.post(
            "/admin/users/1/password",
            json={"new_password": "short"},
        )
        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]

    def test_change_password_user_not_found(self, admin_client):
        """Test changing password for non-existent user."""
        response = admin_client.post(
            "/admin/users/99999/password",
            json={"new_password": "newPassword123"},
        )
        assert response.status_code == 404
