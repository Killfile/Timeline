"""Unit tests for user service."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.services.user_service import (
    create_user,
    get_user,
    list_users,
    update_user,
    delete_user,
    change_user_password,
)


@pytest.fixture
def mock_conn():
    """Mock database connection."""
    conn = Mock()
    cursor = Mock()
    conn.cursor.return_value = cursor
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    return conn


class TestCreateUser:
    """Tests for create_user function."""

    @patch('api.services.user_service.fetch_user_by_email')
    @patch('api.services.user_service.fetch_user_by_id')
    @patch('api.services.user_service.fetch_user_roles')
    def test_create_user_success(self, mock_fetch_roles, mock_fetch_by_id, mock_fetch_by_email, mock_conn):
        """Test successful user creation."""
        # Mock no existing user
        mock_fetch_by_email.return_value = None
        
        # Mock cursor for user insert
        cursor = mock_conn.cursor.return_value
        cursor.fetchone.return_value = {"id": 1}
        cursor.fetchall.return_value = [{"id": 2, "name": "user"}]
        
        # Mock the get_user call at the end
        mock_fetch_by_id.return_value = {
            "id": 1,
            "email": "test@example.com",
            "is_active": True,
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 1),
        }
        mock_fetch_roles.return_value = ["user"]

        result = create_user(
            mock_conn,
            email="test@example.com",
            password="password123",
            roles=["user"],
            is_active=True,
        )

        assert result["id"] == 1
        assert result["email"] == "test@example.com"
        assert result["roles"] == ["user"]
        assert cursor.execute.call_count == 3  # Insert user, fetch role IDs, assign roles

    @patch('api.services.user_service.fetch_user_by_email')
    def test_create_user_duplicate_email(self, mock_fetch_by_email, mock_conn):
        """Test creating user with duplicate email."""
        # Mock existing user
        mock_fetch_by_email.return_value = {
            "id": 1,
            "email": "test@example.com",
            "is_active": True,
        }

        with pytest.raises(ValueError, match="already exists"):
            create_user(
                mock_conn,
                email="test@example.com",
                password="password123",
                roles=["user"],
            )

    def test_create_user_weak_password(self, mock_conn):
        """Test creating user with weak password."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            create_user(
                mock_conn,
                email="test@example.com",
                password="short",
                roles=["user"],
            )

    def test_create_user_invalid_email(self, mock_conn):
        """Test creating user with invalid email."""
        with pytest.raises(ValueError, match="Invalid email"):
            create_user(
                mock_conn,
                email="not-an-email",
                password="password123",
                roles=["user"],
            )

    def test_create_user_invalid_role(self, mock_conn):
        """Test creating user with invalid role."""
        with pytest.raises(ValueError, match="Invalid role"):
            create_user(
                mock_conn,
                email="test@example.com",
                password="password123",
                roles=["invalid_role"],
            )


class TestGetUser:
    """Tests for get_user function."""

    @patch('api.services.user_service.fetch_user_by_id')
    @patch('api.services.user_service.fetch_user_roles')
    def test_get_user_success(self, mock_fetch_roles, mock_fetch_by_id, mock_conn):
        """Test successful user retrieval."""
        mock_fetch_by_id.return_value = {
            "id": 1,
            "email": "test@example.com",
            "is_active": True,
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 1),
        }
        mock_fetch_roles.return_value = ["user"]

        result = get_user(mock_conn, user_id=1)

        assert result["id"] == 1
        assert result["email"] == "test@example.com"
        assert result["roles"] == ["user"]

    @patch('api.services.user_service.fetch_user_by_id')
    def test_get_user_not_found(self, mock_fetch_by_id, mock_conn):
        """Test getting non-existent user."""
        mock_fetch_by_id.return_value = None

        result = get_user(mock_conn, user_id=999)

        assert result is None


class TestListUsers:
    """Tests for list_users function."""

    @patch('api.services.user_service.fetch_user_roles')
    def test_list_users_default_params(self, mock_fetch_roles, mock_conn):
        """Test listing users with default parameters."""
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [
            {"id": 1, "email": "user1@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
            {"id": 2, "email": "user2@example.com", "is_active": True, "created_at": datetime(2026, 1, 2), "updated_at": datetime(2026, 1, 2)},
        ]
        cursor.fetchone.return_value = {"count": 2}
        mock_fetch_roles.return_value = ["user"]

        result = list_users(mock_conn)

        assert len(result["users"]) == 2
        assert result["total"] == 2
        assert result["limit"] == 20
        assert result["offset"] == 0

    @patch('api.services.user_service.fetch_user_roles')
    def test_list_users_with_email_filter(self, mock_fetch_roles, mock_conn):
        """Test listing users with email filter."""
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [
            {"id": 1, "email": "admin@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
        ]
        cursor.fetchone.return_value = {"count": 1}
        mock_fetch_roles.return_value = ["admin"]

        result = list_users(mock_conn, email_filter="admin")

        assert len(result["users"]) == 1
        assert "admin" in result["users"][0]["email"]

    @patch('api.services.user_service.fetch_user_roles')
    def test_list_users_with_role_filter(self, mock_fetch_roles, mock_conn):
        """Test listing users with role filter."""
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = {"count": 0}
        mock_fetch_roles.return_value = []

        result = list_users(mock_conn, role_filter="admin")

        assert len(result["users"]) == 0

    @patch('api.services.user_service.fetch_user_roles')
    def test_list_users_inactive_only(self, mock_fetch_roles, mock_conn):
        """Test listing inactive users."""
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [
            {"id": 3, "email": "inactive@example.com", "is_active": False, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
        ]
        cursor.fetchone.return_value = {"count": 1}
        mock_fetch_roles.return_value = ["user"]

        result = list_users(mock_conn, active_only=False)

        assert len(result["users"]) == 1


class TestUpdateUser:
    """Tests for update_user function."""

    @patch('api.services.user_service.fetch_user_by_id')
    @patch('api.services.user_service.fetch_user_roles')
    def test_update_user_email(self, mock_fetch_roles, mock_fetch_by_id, mock_conn):
        """Test updating user email."""
        # First call to check user exists
        # Second call in get_user at the end
        mock_fetch_by_id.side_effect = [
            {"id": 1, "email": "old@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
            {"id": 1, "email": "new@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
        ]
        mock_fetch_roles.return_value = ["user"]

        result = update_user(mock_conn, user_id=1, email="new@example.com")

        assert result["email"] == "new@example.com"

    @patch('api.services.user_service.fetch_user_by_id')
    @patch('api.services.user_service.fetch_user_roles')
    def test_update_user_roles(self, mock_fetch_roles, mock_fetch_by_id, mock_conn):
        """Test updating user roles."""
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 1, "name": "admin"}]
        
        mock_fetch_by_id.side_effect = [
            {"id": 1, "email": "test@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
            {"id": 1, "email": "test@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
        ]
        mock_fetch_roles.return_value = ["admin"]

        result = update_user(mock_conn, user_id=1, roles=["admin"])

        assert "admin" in result["roles"]

    @patch('api.services.user_service.fetch_user_by_id')
    @patch('api.services.user_service.fetch_user_roles')
    def test_update_user_deactivate(self, mock_fetch_roles, mock_fetch_by_id, mock_conn):
        """Test deactivating user."""
        mock_fetch_by_id.side_effect = [
            {"id": 1, "email": "test@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
            {"id": 1, "email": "test@example.com", "is_active": False, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)},
        ]
        mock_fetch_roles.return_value = ["user"]

        result = update_user(mock_conn, user_id=1, is_active=False)

        assert result["is_active"] is False

    @patch('api.services.user_service.fetch_user_by_id')
    def test_update_user_not_found(self, mock_fetch_by_id, mock_conn):
        """Test updating non-existent user."""
        mock_fetch_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            update_user(mock_conn, user_id=999, email="new@example.com")

    @patch('api.services.user_service.fetch_user_by_id')
    def test_update_user_duplicate_email(self, mock_fetch_by_id, mock_conn):
        """Test updating to duplicate email."""
        cursor = mock_conn.cursor.return_value
        mock_fetch_by_id.return_value = {"id": 1, "email": "test@example.com", "is_active": True, "created_at": datetime(2026, 1, 1), "updated_at": datetime(2026, 1, 1)}
        cursor.execute.side_effect = Exception("duplicate key value violates unique constraint")

        with pytest.raises(ValueError, match="already in use"):
            update_user(mock_conn, user_id=1, email="existing@example.com")


class TestDeleteUser:
    """Tests for delete_user function."""

    @patch('api.services.user_service.fetch_user_by_id')
    def test_delete_user_success(self, mock_fetch_by_id, mock_conn):
        """Test successful user deletion (deactivation)."""
        cursor = mock_conn.cursor.return_value
        mock_fetch_by_id.return_value = {"id": 1, "email": "test@example.com", "is_active": True}

        delete_user(mock_conn, user_id=1)

        cursor.execute.assert_called()  # Should update is_active = False

    @patch('api.services.user_service.fetch_user_by_id')
    def test_delete_user_not_found(self, mock_fetch_by_id, mock_conn):
        """Test deleting non-existent user."""
        mock_fetch_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            delete_user(mock_conn, user_id=999)


class TestChangeUserPassword:
    """Tests for change_user_password function."""

    @patch('api.services.user_service.fetch_user_by_id')
    @patch('api.services.user_service.fetch_user_by_id')
    def test_change_password_success(self, mock_fetch_by_id, mock_conn):
        """Test successful password change."""
        cursor = mock_conn.cursor.return_value
        mock_fetch_by_id.return_value = {"id": 1, "email": "test@example.com"}

        change_user_password(mock_conn, user_id=1, new_password="newPassword123")

        cursor.execute.assert_called()  # Should update password_hash

    def test_change_password_weak(self, mock_conn):
        """Test password change with weak password."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            change_user_password(mock_conn, user_id=1, new_password="weak")

    @patch('api.services.user_service.fetch_user_by_id')
    def test_change_password_user_not_found(self, mock_fetch_by_id, mock_conn):
        """Test password change for non-existent user."""
        mock_fetch_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            change_user_password(mock_conn, user_id=999, new_password="newPassword123")

        with pytest.raises(ValueError, match="not found"):
            change_user_password(mock_conn, user_id=999, new_password="newPassword123")
