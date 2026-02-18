"""User management service layer."""

from __future__ import annotations

from typing import Any
from email_validator import validate_email, EmailNotValidError

from ..auth.password_service import hash_password
from ..models.user import fetch_user_by_email, fetch_user_by_id, fetch_user_roles


VALID_ROLES = {"admin", "user"}
MIN_PASSWORD_LENGTH = 8


def create_user(
    conn,
    email: str,
    password: str,
    roles: list[str],
    is_active: bool = True,
) -> dict[str, Any]:
    """Create a new user with specified roles.
    
    Args:
        conn: Database connection
        email: User email (must be unique and valid)
        password: Plain text password (will be hashed)
        roles: List of role names to assign
        is_active: Whether user is active
        
    Returns:
        Created user dict with id, email, roles, is_active, timestamps
        
    Raises:
        ValueError: If validation fails or user already exists
    """
    # Validate email
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        raise ValueError("Invalid email format")
    
    # Validate password
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    
    # Validate roles
    for role in roles:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Valid roles: {', '.join(VALID_ROLES)}")
    
    # Check if user already exists
    existing_user = fetch_user_by_email(conn, email)
    if existing_user:
        raise ValueError(f"User with email {email} already exists")
    
    # Hash password
    password_hash = hash_password(password)
    
    cursor = conn.cursor()
    try:
        # Insert user
        cursor.execute(
            """
            INSERT INTO users (email, password_hash, is_active)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (email, password_hash, is_active),
        )
        user_row = cursor.fetchone()
        user_id = user_row["id"]
        
        # Assign roles
        if roles:
            # Get role IDs
            placeholders = ','.join(['%s'] * len(roles))
            cursor.execute(
                f"""
                SELECT id, name FROM roles
                WHERE name IN ({placeholders})
                """,
                tuple(roles),
            )
            role_rows = cursor.fetchall()
            role_map = {row["name"]: row["id"] for row in role_rows}
            
            # Insert user_roles
            for role_name in roles:
                role_id = role_map.get(role_name)
                if role_id:
                    cursor.execute(
                        """
                        INSERT INTO user_roles (user_id, role_id)
                        VALUES (%s, %s)
                        """,
                        (user_id, role_id),
                    )
        
        conn.commit()
        
        # Return created user
        return get_user(conn, user_id)
        
    except Exception as e:
        conn.rollback()
        if "duplicate key" in str(e).lower():
            raise ValueError(f"User with email {email} already exists")
        raise
    finally:
        cursor.close()


def get_user(conn, user_id: int) -> dict[str, Any] | None:
    """Get user by ID with roles.
    
    Args:
        conn: Database connection
        user_id: User ID
        
    Returns:
        User dict with roles or None if not found
    """
    user = fetch_user_by_id(conn, user_id)
    if not user:
        return None
    
    roles = fetch_user_roles(conn, user_id)
    
    return {
        "id": user["id"],
        "email": user["email"],
        "is_active": user["is_active"],
        "roles": roles,
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
        "updated_at": user["updated_at"].isoformat() if user.get("updated_at") else None,
    }


def list_users(
    conn,
    limit: int = 20,
    offset: int = 0,
    email_filter: str | None = None,
    role_filter: str | None = None,
    active_only: bool = True,
) -> dict[str, Any]:
    """List users with optional filters.
    
    Args:
        conn: Database connection
        limit: Maximum number of users to return
        offset: Number of users to skip
        email_filter: Filter by email (partial match)
        role_filter: Filter by role name
        active_only: Include only active users
        
    Returns:
        Dict with users list, total count, limit, offset
    """
    cursor = conn.cursor()
    try:
        # Build query
        conditions = []
        params = []
        
        if active_only:
            conditions.append("u.is_active = true")
        
        if email_filter:
            conditions.append("u.email ILIKE %s")
            params.append(f"%{email_filter}%")
        
        if role_filter:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = u.id AND r.name = %s
                )
            """)
            params.append(role_filter)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # Get total count
        cursor.execute(
            f"""
            SELECT COUNT(*) as count
            FROM users u
            {where_clause}
            """,
            tuple(params),
        )
        total = cursor.fetchone()["count"]
        
        # Get users
        params.extend([limit, offset])
        cursor.execute(
            f"""
            SELECT id, email, is_active, created_at, updated_at
            FROM users u
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        )
        user_rows = cursor.fetchall()
        
        # Get roles for each user
        users = []
        for user_row in user_rows:
            user_id = user_row["id"]
            roles = fetch_user_roles(conn, user_id)
            users.append({
                "id": user_row["id"],
                "email": user_row["email"],
                "is_active": user_row["is_active"],
                "roles": roles,
                "created_at": user_row["created_at"].isoformat() if user_row.get("created_at") else None,
                "updated_at": user_row["updated_at"].isoformat() if user_row.get("updated_at") else None,
            })
        
        return {
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
        
    finally:
        cursor.close()


def update_user(
    conn,
    user_id: int,
    email: str | None = None,
    roles: list[str] | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """Update user information.
    
    Args:
        conn: Database connection
        user_id: User ID to update
        email: New email (optional)
        roles: New roles list (optional)
        is_active: New active status (optional)
        
    Returns:
        Updated user dict
        
    Raises:
        ValueError: If user not found or validation fails
    """
    # Check user exists
    user = fetch_user_by_id(conn, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    
    cursor = conn.cursor()
    try:
        # Update email if provided
        if email is not None:
            try:
                validate_email(email, check_deliverability=False)
            except EmailNotValidError:
                raise ValueError("Invalid email format")
            
            cursor.execute(
                """
                UPDATE users
                SET email = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (email, user_id),
            )
        
        # Update active status if provided
        if is_active is not None:
            cursor.execute(
                """
                UPDATE users
                SET is_active = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (is_active, user_id),
            )
        
        # Update roles if provided
        if roles is not None:
            # Validate roles
            for role in roles:
                if role not in VALID_ROLES:
                    raise ValueError(f"Invalid role: {role}")
            
            # Delete existing roles
            cursor.execute(
                """
                DELETE FROM user_roles
                WHERE user_id = %s
                """,
                (user_id,),
            )
            
            # Insert new roles
            if roles:
                # Get role IDs
                placeholders = ','.join(['%s'] * len(roles))
                cursor.execute(
                    f"""
                    SELECT id, name FROM roles
                    WHERE name IN ({placeholders})
                    """,
                    tuple(roles),
                )
                role_rows = cursor.fetchall()
                role_map = {row["name"]: row["id"] for row in role_rows}
                
                # Insert user_roles
                for role_name in roles:
                    role_id = role_map.get(role_name)
                    if role_id:
                        cursor.execute(
                            """
                            INSERT INTO user_roles (user_id, role_id)
                            VALUES (%s, %s)
                            """,
                            (user_id, role_id),
                        )
        
        conn.commit()
        
        # Return updated user
        return get_user(conn, user_id)
        
    except Exception as e:
        conn.rollback()
        if "duplicate key" in str(e).lower():
            raise ValueError(f"Email {email} is already in use")
        raise
    finally:
        cursor.close()


def delete_user(conn, user_id: int) -> None:
    """Delete (deactivate) a user.
    
    Args:
        conn: Database connection
        user_id: User ID to delete
        
    Raises:
        ValueError: If user not found
    """
    # Check user exists
    user = fetch_user_by_id(conn, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    
    cursor = conn.cursor()
    try:
        # Deactivate user (soft delete)
        cursor.execute(
            """
            UPDATE users
            SET is_active = false, updated_at = NOW()
            WHERE id = %s
            """,
            (user_id,),
        )
        conn.commit()
    finally:
        cursor.close()


def change_user_password(conn, user_id: int, new_password: str) -> None:
    """Change a user's password.
    
    Args:
        conn: Database connection
        user_id: User ID
        new_password: New plain text password (will be hashed)
        
    Raises:
        ValueError: If user not found or password validation fails
    """
    # Validate password
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    
    # Check user exists
    user = fetch_user_by_id(conn, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    
    # Hash new password
    password_hash = hash_password(new_password)
    
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE users
            SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (password_hash, user_id),
        )
        conn.commit()
    finally:
        cursor.close()
