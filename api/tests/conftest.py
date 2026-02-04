"""Pytest configuration for API tests."""

import os
import sys
import pytest
from pathlib import Path
import importlib.util

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
