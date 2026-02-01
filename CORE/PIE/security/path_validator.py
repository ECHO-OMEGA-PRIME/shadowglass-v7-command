"""
PIE FILESYSTEM PATH VALIDATOR
Governance Directive: Week 1 Critical Fixes
Classification: SECURITY_HARDENING

EXPLICIT ALLOW-LIST ONLY.
Reject absolute paths outside allow-list.
Reject symlinks.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from loguru import logger


class PathValidationResult(Enum):
    """Path validation result codes."""
    VALID = "VALID"
    REJECTED_NOT_IN_ALLOWLIST = "REJECTED_NOT_IN_ALLOWLIST"
    REJECTED_SYMLINK = "REJECTED_SYMLINK"
    REJECTED_ABSOLUTE_OUTSIDE = "REJECTED_ABSOLUTE_OUTSIDE"
    REJECTED_PATH_TRAVERSAL = "REJECTED_PATH_TRAVERSAL"
    REJECTED_INVALID_PATH = "REJECTED_INVALID_PATH"
    REJECTED_FAIL_CLOSED = "REJECTED_FAIL_CLOSED"


@dataclass
class PathValidation:
    """Path validation result."""
    path: str
    resolved_path: str
    valid: bool
    result: PathValidationResult
    matched_allowlist_entry: Optional[str] = None


class PIEPathValidator:
    """
    Filesystem path validator for PIE ingestion.

    SECURITY PROPERTIES:
    - EXPLICIT ALLOW-LIST ONLY
    - No default paths
    - Reject symlinks
    - Reject path traversal
    - FAIL CLOSED on any error
    """

    def __init__(self, allowlist: list[str]):
        """
        Initialize path validator with explicit allow-list.

        Args:
            allowlist: List of allowed base paths (must be non-empty)

        Raises:
            ValueError: If allowlist is empty
        """
        if not allowlist:
            raise ValueError(
                "PIE Path Validator requires non-empty allowlist. "
                "No default paths. FAIL CLOSED."
            )

        # Normalize and validate allowlist entries
        self._allowlist: list[Path] = []
        for entry in allowlist:
            try:
                resolved = Path(entry).resolve()
                if not resolved.exists():
                    logger.warning(f"Allowlist path does not exist: {entry}")
                self._allowlist.append(resolved)
            except Exception as e:
                raise ValueError(f"Invalid allowlist entry '{entry}': {e}")

        if not self._allowlist:
            raise ValueError("No valid allowlist entries after resolution")

        logger.info(
            f"PIE Path Validator initialized with {len(self._allowlist)} "
            f"allowlist entries"
        )

    def validate(self, path: str) -> PathValidation:
        """
        Validate a path against the allow-list.

        FAIL CLOSED: Any validation error returns invalid result.

        Args:
            path: Path to validate

        Returns:
            PathValidation with result
        """
        # FAIL CLOSED: Empty path
        if not path:
            logger.warning("PATH_REJECT: Empty path")
            return PathValidation(
                path="",
                resolved_path="",
                valid=False,
                result=PathValidationResult.REJECTED_INVALID_PATH
            )

        try:
            input_path = Path(path)
        except Exception as e:
            logger.warning(f"PATH_REJECT: Invalid path syntax: {e}")
            return PathValidation(
                path=path,
                resolved_path="",
                valid=False,
                result=PathValidationResult.REJECTED_INVALID_PATH
            )

        # Check for path traversal attempts BEFORE resolution
        path_str = str(input_path)
        if ".." in path_str:
            logger.warning(f"PATH_REJECT: Path traversal attempt: {path}")
            return PathValidation(
                path=path,
                resolved_path="",
                valid=False,
                result=PathValidationResult.REJECTED_PATH_TRAVERSAL
            )

        # REJECT SYMLINKS
        try:
            if input_path.exists() and input_path.is_symlink():
                logger.warning(f"PATH_REJECT: Symlink rejected: {path}")
                return PathValidation(
                    path=path,
                    resolved_path="",
                    valid=False,
                    result=PathValidationResult.REJECTED_SYMLINK
                )
        except Exception as e:
            # FAIL CLOSED on symlink check error
            logger.error(f"PATH_REJECT: Symlink check failed: {e}")
            return PathValidation(
                path=path,
                resolved_path="",
                valid=False,
                result=PathValidationResult.REJECTED_FAIL_CLOSED
            )

        # Resolve to absolute path
        try:
            resolved = input_path.resolve()
            resolved_str = str(resolved)
        except Exception as e:
            logger.warning(f"PATH_REJECT: Path resolution failed: {e}")
            return PathValidation(
                path=path,
                resolved_path="",
                valid=False,
                result=PathValidationResult.REJECTED_INVALID_PATH
            )

        # Check against allowlist
        matched_entry = None
        for allowed_base in self._allowlist:
            try:
                # Check if resolved path is under allowed base
                resolved.relative_to(allowed_base)
                matched_entry = str(allowed_base)
                break
            except ValueError:
                # Not under this base, continue checking
                continue

        if matched_entry is None:
            logger.warning(
                f"PATH_REJECT: Path not in allowlist: {path} "
                f"(resolved: {resolved_str})"
            )
            return PathValidation(
                path=path,
                resolved_path=resolved_str,
                valid=False,
                result=PathValidationResult.REJECTED_NOT_IN_ALLOWLIST
            )

        # Post-resolution symlink check (defense in depth)
        try:
            # Walk up the path checking for symlinks
            current = resolved
            while current != current.parent:
                if current.is_symlink():
                    logger.warning(
                        f"PATH_REJECT: Symlink in path hierarchy: {current}"
                    )
                    return PathValidation(
                        path=path,
                        resolved_path=resolved_str,
                        valid=False,
                        result=PathValidationResult.REJECTED_SYMLINK
                    )
                current = current.parent
        except Exception as e:
            # FAIL CLOSED
            logger.error(f"PATH_REJECT: Path hierarchy check failed: {e}")
            return PathValidation(
                path=path,
                resolved_path=resolved_str,
                valid=False,
                result=PathValidationResult.REJECTED_FAIL_CLOSED
            )

        # VALID
        logger.info(f"PATH_VALID: {path} (allowlist: {matched_entry})")
        return PathValidation(
            path=path,
            resolved_path=resolved_str,
            valid=True,
            result=PathValidationResult.VALID,
            matched_allowlist_entry=matched_entry
        )

    def get_allowlist(self) -> list[str]:
        """Return copy of allowlist (read-only access)."""
        return [str(p) for p in self._allowlist]


# Default allowlist for PIE artifacts
# EXPLICIT PATHS ONLY - NO WILDCARDS
PIE_ARTIFACT_ALLOWLIST = [
    # PIE corpus directory
    "O:/ECHO_OMEGA_PRIME/CORE/PIE/corpus",
    # PIE staging directory
    "O:/ECHO_OMEGA_PRIME/CORE/PIE/staging/artifacts",
    # Approved external sources (read-only)
    "O:/ECHO_OMEGA_PRIME/CORE/PIE/external/approved",
]


def create_path_validator(
    allowlist: Optional[list[str]] = None
) -> PIEPathValidator:
    """
    Factory function for creating path validator.

    Args:
        allowlist: Custom allowlist (uses PIE_ARTIFACT_ALLOWLIST if None)

    Returns:
        Configured PIEPathValidator

    Raises:
        ValueError: If allowlist is empty or invalid
    """
    # SECURITY: Must use 'is not None' check, not truthy check.
    # Empty list [] must raise ValueError (FAIL CLOSED),
    # not fall back to defaults silently.
    paths = allowlist if allowlist is not None else PIE_ARTIFACT_ALLOWLIST
    return PIEPathValidator(paths)
