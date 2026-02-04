"""
OBSOLETE: Auth dependency tests for Authorization header + Origin validation.

The API has migrated to cookie-based authentication without Origin validation.
Cookie security is enforced by the browser (cannot be set by non-browser clients).

See test_cookie_auth.py for current authentication tests.
"""

import pytest

pytestmark = pytest.mark.skip(reason="Obsolete - API migrated to cookie-based auth")
