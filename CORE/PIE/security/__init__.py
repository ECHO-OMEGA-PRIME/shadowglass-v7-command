"""
PIE SECURITY MODULE
Governance Directive: Week 1 Critical Fixes
Classification: SECURITY_HARDENING

FAIL CLOSED BY DEFAULT.
AUTHORITY_OVERRIDE: PERMANENTLY DISABLED.
"""

from .auth_middleware import (
    PIEAuthMiddleware,
    AuthResult,
    AuthContext,
    create_auth_middleware,
)

from .path_validator import (
    PIEPathValidator,
    PathValidationResult,
    PathValidation,
    PIE_ARTIFACT_ALLOWLIST,
    create_path_validator,
)

from .manifest_verifier import (
    PIEManifestVerifier,
    ManifestResult,
    ManifestVerification,
    ArtifactManifest,
    create_manifest_verifier,
)

from .hardening_config import (
    PIEHardeningConfig,
    PIE_HARDENING_CONFIG,
    AUTHORITY_OVERRIDE_DISABLED,
    get_hardening_config,
    verify_hardening_active,
)

__all__ = [
    # Auth Middleware
    "PIEAuthMiddleware",
    "AuthResult",
    "AuthContext",
    "create_auth_middleware",
    # Path Validator
    "PIEPathValidator",
    "PathValidationResult",
    "PathValidation",
    "PIE_ARTIFACT_ALLOWLIST",
    "create_path_validator",
    # Manifest Verifier
    "PIEManifestVerifier",
    "ManifestResult",
    "ManifestVerification",
    "ArtifactManifest",
    "create_manifest_verifier",
    # Hardening Config
    "PIEHardeningConfig",
    "PIE_HARDENING_CONFIG",
    "AUTHORITY_OVERRIDE_DISABLED",
    "get_hardening_config",
    "verify_hardening_active",
]
