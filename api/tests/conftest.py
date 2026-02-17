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
    
    # Load api.py as a module
    api_file = API_DIR / "api.py"
    spec = importlib.util.spec_from_file_location("api_module", api_file)
    api_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_module)
    
    return TestClient(api_module.app)


@pytest.fixture(scope="function")
def db_cleanup():
    """Clean up test data after each test to ensure idempotency."""
    # Store the initial state (just admin user)
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )
    
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Get admin user ID to preserve it
            cur.execute("SELECT id FROM users WHERE email = 'admin@example.com'")
            admin_row = cur.fetchone()
            admin_id = admin_row[0] if admin_row else None
        
        conn.commit()
        
        yield  # Run the test
        
        # Cleanup after test: delete all users except admin
        with conn.cursor() as cur:
            if admin_id:
                cur.execute("DELETE FROM users WHERE id != %s", (admin_id,))
            else:
                # If no admin, delete all test users (shouldn't happen)
                cur.execute("DELETE FROM users WHERE email != 'admin@example.com'")
        
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
    return test_client

