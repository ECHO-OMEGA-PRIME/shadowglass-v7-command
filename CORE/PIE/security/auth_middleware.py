"""
PIE AUTHENTICATION MIDDLEWARE
Governance Directive: Week 1 Critical Fixes
Classification: SECURITY_HARDENING

FAIL CLOSED BY DEFAULT.
No unauthenticated requests permitted to /engineering/ingest.
"""

import hmac
import hashlib
import time
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from loguru import logger


class AuthResult(Enum):
    """Authentication result codes."""
    SUCCESS = "SUCCESS"
    MISSING_ACTOR_ID = "MISSING_ACTOR_ID"
    MISSING_TOKEN = "MISSING_TOKEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    INSUFFICIENT_AUTHORITY = "INSUFFICIENT_AUTHORITY"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass
class AuthContext:
    """Authenticated request context."""
    actor_id: str
    authority_tier: int
    timestamp: int
    valid: bool
    result: AuthResult


class PIEAuthMiddleware:
    """
    Authentication middleware for PIE ingestion endpoints.

    SECURITY PROPERTIES:
    - FAIL CLOSED: Any error → reject (401)
    - No bypass flags
    - No environment toggles
    - No authority_override
    """

    # Token validity window (5 minutes)
    TOKEN_VALIDITY_SECONDS = 300

    # Minimum authority tier for ingestion
    MIN_INGEST_AUTHORITY = 80  # TIER_80 or higher

    def __init__(self, signing_key: bytes):
        """
        Initialize middleware with signing key.

        Args:
            signing_key: HMAC signing key (must be provided, no defaults)
        """
        if not signing_key or len(signing_key) < 32:
            raise ValueError("Signing key must be at least 32 bytes")

        self._signing_key = signing_key
        self._fail_closed = True  # CANNOT BE CHANGED

        logger.info("PIE Auth Middleware initialized (FAIL_CLOSED=True)")

    def authenticate(
        self,
        actor_id: Optional[str],
        token: Optional[str],
        timestamp: Optional[int] = None
    ) -> AuthContext:
        """
        Authenticate an ingestion request.

        FAIL CLOSED: Any validation failure returns invalid context.

        Args:
            actor_id: Actor identifier (required)
            token: Signed authentication token (required)
            timestamp: Request timestamp (defaults to now)

        Returns:
            AuthContext with authentication result
        """
        # FAIL CLOSED: Missing actor_id
        if not actor_id:
            logger.warning("AUTH_FAIL: Missing actor_id")
            return AuthContext(
                actor_id="",
                authority_tier=0,
                timestamp=0,
                valid=False,
                result=AuthResult.MISSING_ACTOR_ID
            )

        # FAIL CLOSED: Missing token
        if not token:
            logger.warning(f"AUTH_FAIL: Missing token for actor={actor_id}")
            return AuthContext(
                actor_id=actor_id,
                authority_tier=0,
                timestamp=0,
                valid=False,
                result=AuthResult.MISSING_TOKEN
            )

        # Parse timestamp
        request_timestamp = timestamp or int(time.time())

        # Verify token signature
        try:
            is_valid, authority_tier = self._verify_token(
                actor_id, token, request_timestamp
            )
        except Exception as e:
            # FAIL CLOSED: Any exception during verification
            logger.error(f"AUTH_FAIL: Token verification error: {e}")
            return AuthContext(
                actor_id=actor_id,
                authority_tier=0,
                timestamp=request_timestamp,
                valid=False,
                result=AuthResult.FAIL_CLOSED
            )

        if not is_valid:
            logger.warning(f"AUTH_FAIL: Invalid token for actor={actor_id}")
            return AuthContext(
                actor_id=actor_id,
                authority_tier=0,
                timestamp=request_timestamp,
                valid=False,
                result=AuthResult.INVALID_TOKEN
            )

        # Check token expiration
        current_time = int(time.time())
        if abs(current_time - request_timestamp) > self.TOKEN_VALIDITY_SECONDS:
            logger.warning(f"AUTH_FAIL: Expired token for actor={actor_id}")
            return AuthContext(
                actor_id=actor_id,
                authority_tier=authority_tier,
                timestamp=request_timestamp,
                valid=False,
                result=AuthResult.EXPIRED_TOKEN
            )

        # Check authority tier
        if authority_tier < self.MIN_INGEST_AUTHORITY:
            logger.warning(
                f"AUTH_FAIL: Insufficient authority for actor={actor_id} "
                f"(tier={authority_tier}, required={self.MIN_INGEST_AUTHORITY})"
            )
            return AuthContext(
                actor_id=actor_id,
                authority_tier=authority_tier,
                timestamp=request_timestamp,
                valid=False,
                result=AuthResult.INSUFFICIENT_AUTHORITY
            )

        # SUCCESS
        logger.info(f"AUTH_SUCCESS: actor={actor_id}, tier={authority_tier}")
        return AuthContext(
            actor_id=actor_id,
            authority_tier=authority_tier,
            timestamp=request_timestamp,
            valid=True,
            result=AuthResult.SUCCESS
        )

    def _verify_token(
        self,
        actor_id: str,
        token: str,
        timestamp: int
    ) -> tuple[bool, int]:
        """
        Verify token signature and extract authority tier.

        Token format: {authority_tier}:{signature}
        Signature = HMAC-SHA256(signing_key, actor_id:timestamp:authority_tier)

        Returns:
            Tuple of (is_valid, authority_tier)
        """
        # Parse token
        parts = token.split(":")
        if len(parts) != 2:
            return False, 0

        try:
            authority_tier = int(parts[0])
            provided_signature = parts[1]
        except (ValueError, IndexError):
            return False, 0

        # Compute expected signature
        message = f"{actor_id}:{timestamp}:{authority_tier}".encode("utf-8")
        expected_signature = hmac.new(
            self._signing_key,
            message,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_signature, expected_signature):
            return False, 0

        return True, authority_tier

    def generate_token(
        self,
        actor_id: str,
        authority_tier: int,
        timestamp: Optional[int] = None
    ) -> str:
        """
        Generate a signed token for testing/internal use.

        Args:
            actor_id: Actor identifier
            authority_tier: Authority tier (100, 80, 60, etc.)
            timestamp: Token timestamp (defaults to now)

        Returns:
            Signed token string
        """
        ts = timestamp or int(time.time())
        message = f"{actor_id}:{ts}:{authority_tier}".encode("utf-8")
        signature = hmac.new(
            self._signing_key,
            message,
            hashlib.sha256
        ).hexdigest()

        return f"{authority_tier}:{signature}"

    # =========================================================================
    # AUTHORITY_OVERRIDE: PERMANENTLY DISABLED
    # =========================================================================
    # The following code paths have been REMOVED per Governance Directive:
    #
    # - authority_override parameter: REMOVED
    # - AUTHORITY_OVERRIDE environment variable: NOT CHECKED
    # - Runtime flags for bypass: DO NOT EXIST
    # - Emergency override: REQUIRES CODE CHANGE + DEPLOYMENT
    #
    # To modify authentication behavior, change this code and redeploy.
    # There are NO runtime toggles.
    # =========================================================================


def create_auth_middleware(signing_key: Optional[bytes] = None) -> PIEAuthMiddleware:
    """
    Factory function for creating auth middleware.

    FAIL CLOSED: If no signing key provided, raises ValueError.

    Args:
        signing_key: HMAC signing key

    Returns:
        Configured PIEAuthMiddleware

    Raises:
        ValueError: If signing key is missing or invalid
    """
    if not signing_key:
        raise ValueError(
            "PIE Auth Middleware requires signing_key. "
            "No default key. No bypass. FAIL CLOSED."
        )

    return PIEAuthMiddleware(signing_key)
