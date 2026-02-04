"""
OBSOLETE: These tests were for Authorization header + X-Client-Secret auth.

The API has migrated to cookie-based authentication.
See test_cookie_auth.py for current token endpoint tests.
"""

import pytest

pytestmark = pytest.mark.skip(reason="Obsolete - API migrated to cookie-based auth")
