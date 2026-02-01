"""
PIE FastAPI Dependencies
Governance Directive: PATCH DIRECTIVE - FastAPI Wiring

Wires existing security middleware into FastAPI dependencies.
NO NEW SECURITY LOGIC - only wiring.
"""

import os
import time
from typing import Optional
from fastapi import Header, HTTPException, Request
from loguru import logger

from ..security import (
    PIEAuthMiddleware,
    AuthResult,
    create_auth_middleware,
)


# Signing key from environment (must be set in production)
_SIGNING_KEY: Optional[bytes] = None
_AUTH_MIDDLEWARE: Optional[PIEAuthMiddleware] = None


def _get_auth_middleware() -> PIEAuthMiddleware:
    """Get or create auth middleware singleton."""
    global _SIGNING_KEY, _AUTH_MIDDLEWARE

    if _AUTH_MIDDLEWARE is None:
        key_str = os.environ.get("PIE_SIGNING_KEY")
        if key_str:
            _SIGNING_KEY = key_str.encode()
        else:
            # For testing only - generate ephemeral key
            logger.warning(
                "PIE_SIGNING_KEY not set - using ephemeral key (NOT FOR PRODUCTION)"
            )
            _SIGNING_KEY = os.urandom(32)

        _AUTH_MIDDLEWARE = create_auth_middleware(_SIGNING_KEY)

    return _AUTH_MIDDLEWARE


async def require_ingest_auth(
    request: Request,
    x_pie_actor_id: Optional[str] = Header(None, alias="X-PIE-Actor-ID"),
    x_pie_token: Optional[str] = Header(None, alias="X-PIE-Token"),
    x_pie_timestamp: Optional[str] = Header(None, alias="X-PIE-Timestamp"),
) -> dict:
    """
    FastAPI dependency for ingestion authentication.

    Enforces FAIL CLOSED behavior BEFORE handler execution.

    Headers required:
        X-PIE-Actor-ID: Actor identifier
        X-PIE-Token: Signed auth token (format: {tier}:{signature})
        X-PIE-Timestamp: Unix timestamp

    Returns:
        Auth context dict with actor_id and authority_tier

    Raises:
        HTTPException: 401/403 on any auth failure
    """
    middleware = _get_auth_middleware()

    # Parse timestamp
    timestamp = None
    if x_pie_timestamp:
        try:
            timestamp = int(x_pie_timestamp)
        except ValueError:
            logger.warning(f"AUTH_FAIL: Invalid timestamp format: {x_pie_timestamp}")
            raise HTTPException(
                status_code=401,
                detail="Invalid timestamp format"
            )

    # Authenticate using existing middleware
    result = middleware.authenticate(
        actor_id=x_pie_actor_id,
        token=x_pie_token,
        timestamp=timestamp
    )

    # Map auth result to HTTP status
    if not result.valid:
        if result.result == AuthResult.INSUFFICIENT_AUTHORITY:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient authority: requires TIER_80+, got TIER_{result.authority_tier or 0}"
            )
        else:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {result.result.value}"
            )

    # Return auth context for handler use
    return {
        "actor_id": result.actor_id,
        "authority_tier": result.authority_tier
    }


def generate_test_token(
    actor_id: str,
    authority_tier: int = 80
) -> tuple[str, int]:
    """
    Generate a valid test token (for testing only).

    Returns:
        Tuple of (token, timestamp)
    """
    middleware = _get_auth_middleware()
    timestamp = int(time.time())
    token = middleware.generate_token(actor_id, authority_tier, timestamp)
    return token, timestamp
