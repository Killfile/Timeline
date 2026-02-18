"""User data access helpers."""

from __future__ import annotations

from typing import Any


def fetch_user_by_email(conn, email: str) -> dict[str, Any] | None:
    """Fetch a user by email address.

    Args:
        conn: Database connection.
        email: User email (case-insensitive match should be applied by caller if needed).

    Returns:
        User row dict or None if not found.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, email, password_hash, is_active, created_at, updated_at
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def fetch_user_by_id(conn, user_id: int) -> dict[str, Any] | None:
    """Fetch a user by id."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, email, password_hash, is_active, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def fetch_user_roles(conn, user_id: int) -> list[str]:
    """Fetch role names for a given user id."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT r.name
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s
            ORDER BY r.name
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [row["name"] for row in rows]
    finally:
        cursor.close()
