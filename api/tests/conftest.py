"""Pytest configuration for API tests."""

import os
import sys
import pytest
from pathlib import Path
import importlib.util
import psycopg2
from psycopg2.extras import DictCursor

# Add api directory to sys.path so relative imports work
API_DIR = Path(__file__).parent.parent.resolve()
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# Set default environment variables for testing before any imports
# This ensures api.py can be imported without errors
os.environ.setdefault("API_JWT_SECRET", "test-jwt-secret-67890")
os.environ.setdefault("COOKIE_NAME", "timeline_auth_test")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COOKIE_SAMESITE", "lax")

# Database connection defaults
# Default to localhost:5433 (local test database) for developer convenience
# Docker containers override POSTGRES_HOST to "database" via docker-compose.yml
os.environ.setdefault("POSTGRES_HOST", "localhost")  # Overridden to "database" in Docker
if os.environ["POSTGRES_HOST"] == "database":
    # Docker execution: use Docker service discovery
    os.environ.setdefault("DB_HOST", "database")
    os.environ.setdefault("DB_PORT", "5432")
else:
    # Local testing: connect to test database on non-standard port
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "5433")

# Common database settings for both environments
os.environ.setdefault("DB_NAME", "timeline_history")
os.environ.setdefault("DB_USER", "timeline_user")
os.environ.setdefault("DB_PASSWORD", "timeline_pass")


@pytest.fixture
def test_client():
    """Provide a FastAPI TestClient for integration tests."""
    from fastapi.testclient import TestClient
    
    # Import api.api directly using the package structure
    import sys
    sys.path.insert(0, str(API_DIR.parent))
    from api.api import app
    
    return TestClient(app)


@pytest.fixture(scope="function")
def db_cleanup():
    """Clean up test data before and after each test to ensure idempotency."""
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    
    try:
        # Get admin user ID to preserve it
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT id FROM users WHERE email = 'admin@example.com'")
            admin_row = cur.fetchone()
            admin_id = admin_row[0] if admin_row else None
        conn.commit()
        
        # CLEANUP BEFORE TEST: Delete all categories to ensure clean test slate
        with conn.cursor() as cur:
            # DELETE CASCADE is already set up on the timeline_categories table
            # so this will cascade delete all related events
            cur.execute("DELETE FROM timeline_categories")
        conn.commit()
        
        yield  # Run the test
        
        # CLEANUP AFTER TEST: Delete all categories and other users (except admin)
        with conn.cursor() as cur:
            # Delete all categories (cascade delete to events)
            cur.execute("DELETE FROM timeline_categories")
            
            # Delete all users except admin
            if admin_id:
                cur.execute("DELETE FROM users WHERE id != %s", (admin_id,))
        
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def admin_client(test_client, db_cleanup):
    """Test client with admin authentication and database cleanup."""
    # Get admin token by logging in
    response = test_client.post(
        "/admin/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    
    # The TestClient automatically stores and sends cookies from the response
    # So the test_client should now have the auth cookie set
    return test_client

