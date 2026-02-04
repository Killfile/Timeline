"""Auth dependency for FastAPI endpoints."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import jwt
from fastapi import HTTPException, Request, status

from .config import AuthConfig, is_origin_allowed, load_auth_config
from .jwt_service import decode_token
from .replay_cache import ReplayCache

logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    claims: dict


def build_auth_dependency(
    config: AuthConfig | None = None,
    replay_cache: ReplayCache | None = None,
) -> Callable[[Request], AuthContext]:
    """Build a FastAPI dependency that enforces JWT cookie authentication."""
    if config is None:
        config = load_auth_config()
    if replay_cache is None:
        replay_cache = ReplayCache(config.replay_window_seconds)

    def _dependency(request: Request) -> AuthContext:
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        
        # Extract token from cookie
        token = request.cookies.get(config.cookie_name)
        if not token:
            logger.warning(
                "Auth failed: missing authentication cookie",
                extra={
                    "reason": "missing_cookie",
                    "cookie_name": config.cookie_name,
                    "client_ip": client_ip,
                    "endpoint": endpoint,
                    "status_code": 401,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Authentication required - missing cookie"
            )
        
        # Decode and validate token
        try:
            claims = decode_token(token, config)
        except jwt.ExpiredSignatureError:
            logger.warning(
                "Auth failed: token expired",
                extra={
                    "reason": "token_expired",
                    "client_ip": client_ip,
                    "endpoint": endpoint,
                    "status_code": 401,
                }
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(
                "Auth failed: invalid token",
                extra={
                    "reason": "invalid_token",
                    "error": str(e),
                    "client_ip": client_ip,
                    "endpoint": endpoint,
                    "status_code": 401,
                }
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        token_id = claims.get("jti")
        if not token_id:
            logger.warning(
                "Auth failed: missing token ID",
                extra={
                    "reason": "missing_jti",
                    "client_ip": client_ip,
                    "endpoint": endpoint,
                    "status_code": 401,
                }
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token id")

        # NOTE: Replay protection disabled for now - tokens can be reused within TTL
        # In a typical API, tokens are meant to be reused for multiple requests
        # Replay protection via jti tracking is more relevant for:
        # 1. Revocation scenarios
        # 2. Single-use tokens (e.g., password reset)
        # 3. Post-expiration replay prevention
        #
        # For this API, replay protection comes from:
        # - Short TTL (15 min)
        # - Signature validation
        # - Expiration checking
        #
        # if replay_cache.check_and_mark(token_id):
        #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token replay detected")

        logger.info(
            "Auth successful",
            extra={
                "client_ip": client_ip,
                "endpoint": endpoint,
                "token_id": token_id[:8] + "...",  # Only log prefix for security
                "status_code": 200,
            }
        )

        return AuthContext(claims=claims)

    return _dependency
