"""
PIE HARDENING CONFIGURATION
Governance Directive: Week 1 Critical Fixes
Classification: SECURITY_HARDENING

AUTHORITY_OVERRIDE: PERMANENTLY DISABLED
No runtime flags. No environment toggles. No bypass.
"""

from dataclasses import dataclass
from typing import Final
from loguru import logger


# =============================================================================
# AUTHORITY_OVERRIDE: PERMANENTLY DISABLED
# =============================================================================
#
# Per Governance Directive PIE_HARDENING_WEEK1:
#
# The authority_override capability has been REMOVED from PIE.
#
# Previous behavior (REMOVED):
#   - authority_override parameter on ingestion endpoints
#   - AUTHORITY_OVERRIDE environment variable
#   - Runtime flags to bypass authentication
#   - Emergency override tokens
#
# Current behavior (PERMANENT):
#   - All requests require authentication
#   - All requests require TIER_80+ authority
#   - No bypass mechanism exists
#   - To change: modify code and redeploy
#
# =============================================================================

# This constant documents that override is disabled.
# It is not checked at runtime - there is no code path that uses it.
AUTHORITY_OVERRIDE_DISABLED: Final[bool] = True


@dataclass(frozen=True)
class PIEHardeningConfig:
    """
    Immutable hardening configuration for PIE.

    All values are compile-time constants.
    No runtime modification permitted.
    """

    # Authentication
    require_authentication: bool = True
    min_authority_tier: int = 80
    token_validity_seconds: int = 300

    # Authority Override (DISABLED)
    authority_override_enabled: bool = False  # PERMANENTLY FALSE

    # Path Validation
    require_path_allowlist: bool = True
    reject_symlinks: bool = True
    reject_path_traversal: bool = True

    # Manifest Verification
    require_signed_manifest: bool = True
    require_hash_verification: bool = True

    # Fail Closed Behavior
    fail_closed: bool = True  # CANNOT BE CHANGED

    def __post_init__(self) -> None:
        """Validate configuration constraints."""
        # Ensure authority_override is disabled
        if self.authority_override_enabled:
            raise ValueError(
                "SECURITY VIOLATION: authority_override cannot be enabled. "
                "This value is permanently False per Governance Directive."
            )

        # Ensure fail_closed is True
        if not self.fail_closed:
            raise ValueError(
                "SECURITY VIOLATION: fail_closed must be True. "
                "PIE always fails closed."
            )

        logger.info("PIE Hardening Config validated (authority_override=DISABLED)")


# Singleton configuration instance
# This is the ONLY valid configuration for PIE
PIE_HARDENING_CONFIG: Final[PIEHardeningConfig] = PIEHardeningConfig()


def get_hardening_config() -> PIEHardeningConfig:
    """
    Get the PIE hardening configuration.

    Returns:
        The singleton PIEHardeningConfig instance

    Note:
        Configuration is immutable. There are no parameters to modify.
    """
    return PIE_HARDENING_CONFIG


# =============================================================================
# REMOVED CODE PATHS
# =============================================================================
#
# The following functions/code paths have been REMOVED:
#
# 1. check_authority_override() - REMOVED
#    Previously checked AUTHORITY_OVERRIDE env var
#
# 2. apply_override_token() - REMOVED
#    Previously allowed bypassing authentication with special token
#
# 3. emergency_bypass() - REMOVED
#    Previously allowed admin bypass during incidents
#
# 4. set_override_flag() - REMOVED
#    Previously set runtime override flag
#
# 5. get_override_status() - REMOVED
#    Previously returned override status
#
# These functions DO NOT EXIST. Any code calling them will fail.
# This is intentional per Governance Directive.
#
# =============================================================================


def verify_hardening_active() -> bool:
    """
    Verify that hardening configuration is active.

    Returns:
        True if hardening is properly configured

    Raises:
        RuntimeError: If hardening is misconfigured
    """
    config = get_hardening_config()

    checks = [
        ("authentication_required", config.require_authentication),
        ("authority_override_disabled", not config.authority_override_enabled),
        ("path_allowlist_required", config.require_path_allowlist),
        ("symlinks_rejected", config.reject_symlinks),
        ("signed_manifests_required", config.require_signed_manifest),
        ("hash_verification_required", config.require_hash_verification),
        ("fail_closed_enabled", config.fail_closed),
    ]

    failed = [name for name, value in checks if not value]

    if failed:
        raise RuntimeError(
            f"PIE Hardening verification failed. "
            f"Failed checks: {', '.join(failed)}"
        )

    logger.info("PIE Hardening verification: ALL CHECKS PASSED")
    return True
