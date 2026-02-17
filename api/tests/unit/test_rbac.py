from __future__ import annotations

import pytest
from fastapi import HTTPException, status

from api.auth.rbac import Principal, principal_from_claims, require_roles, require_scopes


def test_principal_from_claims_defaults_missing_values() -> None:
    principal = principal_from_claims({"sub": "user-1"})

    assert principal.user_id == "user-1"
    assert principal.roles == set()
    assert principal.scopes == set()


def test_require_roles_allows_matching_role() -> None:
    principal = Principal(user_id="user-1", roles={"admin"}, scopes=set(), claims={})

    checker = require_roles({"admin"})
    assert checker(principal) == principal


def test_require_roles_rejects_missing_role() -> None:
    principal = Principal(user_id="user-1", roles={"user"}, scopes=set(), claims={})

    checker = require_roles({"admin"})
    with pytest.raises(HTTPException) as excinfo:
        checker(principal)

    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN


def test_require_scopes_allows_required_scopes() -> None:
    principal = Principal(user_id="user-1", roles=set(), scopes={"users:write"}, claims={})

    checker = require_scopes({"users:write"})
    assert checker(principal) == principal


def test_require_scopes_rejects_missing_scopes() -> None:
    principal = Principal(user_id="user-1", roles=set(), scopes={"users:read"}, claims={})

    checker = require_scopes({"users:write"})
    with pytest.raises(HTTPException) as excinfo:
        checker(principal)

    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
