"""Role-based access control utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from fastapi import Depends, HTTPException, status

from .auth_dependency import AuthContext, build_auth_dependency


@dataclass(frozen=True)
class Principal:
    user_id: str | None
    roles: set[str]
    scopes: set[str]
    claims: dict[str, Any]


def principal_from_claims(claims: dict[str, Any]) -> Principal:
    """Build a principal from JWT claims."""
    return Principal(
        user_id=claims.get("sub"),
        roles=set(claims.get("roles", []) or []),
        scopes=set(claims.get("scopes", []) or []),
        claims=claims,
    )


def get_current_principal(
    auth: AuthContext = Depends(build_auth_dependency()),
) -> Principal:
    """Extract the current principal from an authenticated request."""
    return principal_from_claims(auth.claims)


def _ensure_set(values: Iterable[str]) -> set[str]:
    return set(values)


def require_roles(required_roles: Iterable[str]) -> Callable[[Principal], Principal]:
    """Dependency factory to require at least one of the specified roles."""
    required = _ensure_set(required_roles)

    def _checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not required.intersection(principal.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {sorted(required)}",
            )
        return principal

    return _checker


def require_scopes(required_scopes: Iterable[str]) -> Callable[[Principal], Principal]:
    """Dependency factory to require all specified scopes."""
    required = _ensure_set(required_scopes)

    def _checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not required.issubset(principal.scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required scopes: {sorted(required)}",
            )
        return principal

    return _checker
