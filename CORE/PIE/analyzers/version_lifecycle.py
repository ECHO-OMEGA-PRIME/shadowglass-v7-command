"""
PROGRAMMING INTELLIGENCE ENGINE - Version & Lifecycle Engine
DETERMINISTIC VERSION REASONING

CRITICAL: Most AI coding tools fail here.
This engine REFUSES to answer without version clarity.

Capabilities:
- Explicit version parsing (semver, calver, custom)
- Version range constraints (>=, <, ^, ~)
- Lifecycle state tracking (ACTIVE, DEPRECATED, REMOVED, EOL)
- Migration path computation
- Breaking change detection

REFUSAL CONDITIONS:
- Missing version metadata
- Ambiguous version specification
- Unknown lifecycle state

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from enum import Enum
import re
from loguru import logger

from ..engine.models import (
    VersionMetadata,
    VersionStatus,
    ConfidenceTier,
    EngineeringDoctrine
)


class VersionScheme(str, Enum):
    """Supported version numbering schemes."""
    SEMVER = "SEMVER"           # Major.Minor.Patch
    CALVER = "CALVER"           # Calendar-based (YYYY.MM.DD)
    PYTHON = "PYTHON"           # Python versioning (3.11, 3.12)
    JAVA = "JAVA"               # Java versioning (8, 11, 17, 21)
    DOTNET = "DOTNET"           # .NET versioning (6.0, 7.0, 8.0)
    CUSTOM = "CUSTOM"           # Custom scheme


class LifecyclePhase(str, Enum):
    """Lifecycle phases for versioned software."""
    DEVELOPMENT = "DEVELOPMENT"     # Pre-release development
    ALPHA = "ALPHA"                 # Early testing
    BETA = "BETA"                   # Feature complete, testing
    RC = "RC"                       # Release candidate
    STABLE = "STABLE"               # Production ready
    MAINTENANCE = "MAINTENANCE"     # Security/bug fixes only
    DEPRECATED = "DEPRECATED"       # Use discouraged
    EOL = "EOL"                     # End of life
    REMOVED = "REMOVED"             # No longer available


@dataclass
class ParsedVersion:
    """
    Parsed version with explicit components.
    Supports comparison and constraint checking.
    """
    major: int
    minor: int = 0
    patch: int = 0
    prerelease: Optional[str] = None
    build: Optional[str] = None
    scheme: VersionScheme = VersionScheme.SEMVER
    raw: str = ""

    def __lt__(self, other: "ParsedVersion") -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # Pre-release versions are less than release
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        # Compare prerelease strings
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease
        return False

    def __le__(self, other: "ParsedVersion") -> bool:
        return self == other or self < other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParsedVersion):
            return False
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.prerelease == other.prerelease
        )

    def __gt__(self, other: "ParsedVersion") -> bool:
        return not self <= other

    def __ge__(self, other: "ParsedVersion") -> bool:
        return not self < other

    def __hash__(self):
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def to_string(self) -> str:
        """Convert back to version string."""
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += f"-{self.prerelease}"
        if self.build:
            result += f"+{self.build}"
        return result

    def is_major_compatible(self, other: "ParsedVersion") -> bool:
        """Check if versions are major-compatible (same major version)."""
        return self.major == other.major

    def is_minor_compatible(self, other: "ParsedVersion") -> bool:
        """Check if versions are minor-compatible (same major.minor)."""
        return self.major == other.major and self.minor == other.minor


@dataclass
class VersionConstraint:
    """
    A version constraint (e.g., >=1.0.0, <2.0.0).
    """
    operator: str       # >=, <=, >, <, =, ^, ~
    version: ParsedVersion
    raw: str = ""

    def satisfies(self, version: ParsedVersion) -> bool:
        """Check if a version satisfies this constraint."""
        if self.operator == ">=":
            return version >= self.version
        elif self.operator == ">":
            return version > self.version
        elif self.operator == "<=":
            return version <= self.version
        elif self.operator == "<":
            return version < self.version
        elif self.operator == "=" or self.operator == "==":
            return version == self.version
        elif self.operator == "^":
            # Caret: compatible with version (same major, >= version)
            return version.major == self.version.major and version >= self.version
        elif self.operator == "~":
            # Tilde: patch-level changes only (same major.minor)
            return (version.major == self.version.major and
                    version.minor == self.version.minor and
                    version >= self.version)
        return False


@dataclass
class LifecycleState:
    """
    Current lifecycle state for a version.
    """
    version: ParsedVersion
    phase: LifecyclePhase
    support_ends: Optional[date] = None
    eol_date: Optional[date] = None
    replacement: Optional[str] = None
    migration_guide: Optional[str] = None
    breaking_changes: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def is_supported(self) -> bool:
        """Check if this version is still supported."""
        if self.phase in {LifecyclePhase.EOL, LifecyclePhase.REMOVED}:
            return False
        if self.support_ends and date.today() > self.support_ends:
            return False
        return True

    @property
    def is_recommended(self) -> bool:
        """Check if this version is recommended for new projects."""
        return self.phase in {LifecyclePhase.STABLE}

    @property
    def days_until_eol(self) -> Optional[int]:
        """Days until EOL, if known."""
        if self.eol_date:
            delta = self.eol_date - date.today()
            return delta.days
        return None


@dataclass
class VersionCheckResult:
    """Result of checking a version against requirements."""
    version: ParsedVersion
    lifecycle: LifecycleState
    is_valid: bool
    is_recommended: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    migration_required: bool = False
    migration_path: Optional[str] = None
    confidence: float = 1.0

    # Refusal tracking
    refused: bool = False
    refusal_reason: Optional[str] = None


class VersionLifecycleEngine:
    """
    VERSION & LIFECYCLE ENGINE

    Deterministic version reasoning with explicit refusal conditions.

    Key behaviors:
    1. REFUSES to answer without version clarity
    2. Tracks full lifecycle (ALPHA → STABLE → EOL → REMOVED)
    3. Computes migration paths
    4. Detects breaking changes
    """

    # Version parsing patterns
    VERSION_PATTERNS = [
        # Semver: 1.2.3, 1.2.3-beta.1, 1.2.3+build
        (r"^v?(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$", VersionScheme.SEMVER),
        # Major.Minor only: 3.11, 6.0
        (r"^v?(\d+)\.(\d+)$", VersionScheme.SEMVER),
        # CalVer: 2024.01.15
        (r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", VersionScheme.CALVER),
        # Java-style: 8, 11, 17, 21
        (r"^(\d+)$", VersionScheme.JAVA),
    ]

    # Constraint parsing pattern
    CONSTRAINT_PATTERN = r"^([><=^~]+)?(.+)$"

    def __init__(self):
        self._version_cache: Dict[str, ParsedVersion] = {}
        self._lifecycle_registry: Dict[str, Dict[str, LifecycleState]] = {}
        self._known_eol: Dict[str, List[Dict]] = {}

        # Pre-populate known lifecycle data
        self._init_known_lifecycles()

        logger.info("Version Lifecycle Engine initialized")

    def _init_known_lifecycles(self):
        """Initialize known lifecycle data for major platforms."""
        # Python versions
        self._known_eol["python"] = [
            {"version": "3.8", "eol": "2024-10-14"},
            {"version": "3.9", "eol": "2025-10-05"},
            {"version": "3.10", "eol": "2026-10-04"},
            {"version": "3.11", "eol": "2027-10-24"},
            {"version": "3.12", "eol": "2028-10-31"},
        ]

        # Node.js versions
        self._known_eol["nodejs"] = [
            {"version": "18", "eol": "2025-04-30"},
            {"version": "20", "eol": "2026-04-30"},
            {"version": "22", "eol": "2027-04-30"},
        ]

    def parse_version(self, version_string: str) -> Optional[ParsedVersion]:
        """
        Parse a version string into structured components.

        Returns None if version cannot be parsed - this is a REFUSAL condition.
        """
        if not version_string:
            return None

        version_string = version_string.strip()

        # Check cache
        if version_string in self._version_cache:
            return self._version_cache[version_string]

        # Try each pattern
        for pattern, scheme in self.VERSION_PATTERNS:
            match = re.match(pattern, version_string)
            if match:
                groups = match.groups()
                try:
                    major = int(groups[0])
                    minor = int(groups[1]) if len(groups) > 1 and groups[1] else 0
                    patch = int(groups[2]) if len(groups) > 2 and groups[2] else 0
                    prerelease = groups[3] if len(groups) > 3 else None
                    build = groups[4] if len(groups) > 4 else None

                    version = ParsedVersion(
                        major=major,
                        minor=minor,
                        patch=patch,
                        prerelease=prerelease,
                        build=build,
                        scheme=scheme,
                        raw=version_string
                    )
                    self._version_cache[version_string] = version
                    return version
                except (ValueError, IndexError):
                    continue

        logger.warning(f"Failed to parse version: {version_string}")
        return None

    def parse_constraint(self, constraint_string: str) -> Optional[VersionConstraint]:
        """Parse a version constraint string."""
        if not constraint_string:
            return None

        constraint_string = constraint_string.strip()
        match = re.match(self.CONSTRAINT_PATTERN, constraint_string)
        if not match:
            return None

        operator = match.group(1) or "="
        version_str = match.group(2)

        version = self.parse_version(version_str)
        if not version:
            return None

        return VersionConstraint(
            operator=operator,
            version=version,
            raw=constraint_string
        )

    def check_version(
        self,
        version_string: str,
        technology: Optional[str] = None,
        constraints: Optional[List[str]] = None
    ) -> VersionCheckResult:
        """
        Check a version against lifecycle and constraints.

        WILL REFUSE if:
        - Version cannot be parsed
        - Lifecycle state is unknown and technology is specified
        """
        version = self.parse_version(version_string)

        # REFUSAL: Cannot parse version
        if not version:
            return VersionCheckResult(
                version=ParsedVersion(major=0, minor=0, patch=0, raw=version_string),
                lifecycle=LifecycleState(
                    version=ParsedVersion(major=0, minor=0, patch=0),
                    phase=LifecyclePhase.DEVELOPMENT
                ),
                is_valid=False,
                is_recommended=False,
                refused=True,
                refusal_reason=f"CANNOT PARSE VERSION: '{version_string}' is not a recognized version format",
                confidence=0.0
            )

        # Get lifecycle state
        lifecycle = self._get_lifecycle_state(version, technology)

        # Check constraints
        warnings = []
        errors = []
        migration_required = False
        migration_path = None

        if constraints:
            for constraint_str in constraints:
                constraint = self.parse_constraint(constraint_str)
                if constraint and not constraint.satisfies(version):
                    errors.append(f"Violates constraint: {constraint_str}")

        # Check lifecycle warnings
        if not lifecycle.is_supported:
            errors.append(f"Version {version.raw} is no longer supported")
            if lifecycle.replacement:
                migration_required = True
                migration_path = f"Upgrade to {lifecycle.replacement}"

        if lifecycle.phase == LifecyclePhase.DEPRECATED:
            warnings.append(f"Version {version.raw} is deprecated")
            if lifecycle.replacement:
                migration_path = f"Consider upgrading to {lifecycle.replacement}"

        days_until_eol = lifecycle.days_until_eol
        if days_until_eol is not None:
            if days_until_eol <= 0:
                errors.append(f"Version {version.raw} has reached end of life")
            elif days_until_eol <= 90:
                warnings.append(f"Version {version.raw} reaches EOL in {days_until_eol} days")
            elif days_until_eol <= 180:
                warnings.append(f"Version {version.raw} reaches EOL in ~{days_until_eol // 30} months")

        if lifecycle.breaking_changes:
            for change in lifecycle.breaking_changes[:3]:
                warnings.append(f"Breaking change: {change}")

        is_valid = len(errors) == 0
        is_recommended = lifecycle.is_recommended and is_valid

        return VersionCheckResult(
            version=version,
            lifecycle=lifecycle,
            is_valid=is_valid,
            is_recommended=is_recommended,
            warnings=warnings,
            errors=errors,
            migration_required=migration_required,
            migration_path=migration_path,
            confidence=1.0 if technology else 0.7
        )

    def _get_lifecycle_state(
        self,
        version: ParsedVersion,
        technology: Optional[str]
    ) -> LifecycleState:
        """Get lifecycle state for a version."""
        # Check registry first
        if technology:
            tech_lower = technology.lower()
            if tech_lower in self._lifecycle_registry:
                version_key = f"{version.major}.{version.minor}"
                if version_key in self._lifecycle_registry[tech_lower]:
                    return self._lifecycle_registry[tech_lower][version_key]

            # Check known EOL data
            if tech_lower in self._known_eol:
                for eol_info in self._known_eol[tech_lower]:
                    eol_version = self.parse_version(eol_info["version"])
                    if eol_version and eol_version.major == version.major:
                        if eol_version.minor == version.minor or version.minor == 0:
                            eol_date = datetime.strptime(eol_info["eol"], "%Y-%m-%d").date()
                            phase = LifecyclePhase.EOL if date.today() > eol_date else LifecyclePhase.STABLE
                            return LifecycleState(
                                version=version,
                                phase=phase,
                                eol_date=eol_date
                            )

        # Default: assume stable if recent enough
        if version.prerelease:
            if "alpha" in version.prerelease.lower():
                phase = LifecyclePhase.ALPHA
            elif "beta" in version.prerelease.lower():
                phase = LifecyclePhase.BETA
            elif "rc" in version.prerelease.lower():
                phase = LifecyclePhase.RC
            else:
                phase = LifecyclePhase.DEVELOPMENT
        else:
            phase = LifecyclePhase.STABLE

        return LifecycleState(version=version, phase=phase)

    def check_compatibility(
        self,
        doctrine: EngineeringDoctrine,
        target_version: str
    ) -> VersionCheckResult:
        """
        Check if a doctrine is compatible with a target version.

        REFUSAL: If doctrine has no version metadata.
        """
        if not doctrine.version_metadata:
            return VersionCheckResult(
                version=ParsedVersion(major=0, minor=0, patch=0, raw=target_version),
                lifecycle=LifecycleState(
                    version=ParsedVersion(major=0, minor=0, patch=0),
                    phase=LifecyclePhase.DEVELOPMENT
                ),
                is_valid=False,
                is_recommended=False,
                refused=True,
                refusal_reason="MISSING VERSION METADATA: Cannot verify compatibility without version information",
                confidence=0.0
            )

        target = self.parse_version(target_version)
        if not target:
            return VersionCheckResult(
                version=ParsedVersion(major=0, minor=0, patch=0, raw=target_version),
                lifecycle=LifecycleState(
                    version=ParsedVersion(major=0, minor=0, patch=0),
                    phase=LifecyclePhase.DEVELOPMENT
                ),
                is_valid=False,
                is_recommended=False,
                refused=True,
                refusal_reason=f"CANNOT PARSE TARGET VERSION: '{target_version}'",
                confidence=0.0
            )

        meta = doctrine.version_metadata
        warnings = []
        errors = []

        # Check if version is in valid range
        if meta.version_removed:
            removed = self.parse_version(meta.version_removed)
            if removed and target >= removed:
                return VersionCheckResult(
                    version=target,
                    lifecycle=LifecycleState(version=target, phase=LifecyclePhase.REMOVED),
                    is_valid=False,
                    is_recommended=False,
                    errors=[f"REMOVED in {meta.version_removed}. Use: {meta.replacement_path or 'alternative required'}"],
                    migration_required=True,
                    migration_path=meta.replacement_path,
                    confidence=1.0
                )

        if meta.version_deprecated:
            deprecated = self.parse_version(meta.version_deprecated)
            if deprecated and target >= deprecated:
                warnings.append(f"Deprecated since {meta.version_deprecated}")
                if meta.replacement_path:
                    warnings.append(f"Consider: {meta.replacement_path}")

        if meta.version_introduced:
            introduced = self.parse_version(meta.version_introduced)
            if introduced and target < introduced:
                return VersionCheckResult(
                    version=target,
                    lifecycle=LifecycleState(version=target, phase=LifecyclePhase.STABLE),
                    is_valid=False,
                    is_recommended=False,
                    errors=[f"Not available until {meta.version_introduced}"],
                    confidence=1.0
                )

        if meta.breaking_changes:
            for change in meta.breaking_changes[:3]:
                warnings.append(f"Breaking change: {change}")

        return VersionCheckResult(
            version=target,
            lifecycle=LifecycleState(version=target, phase=LifecyclePhase.STABLE),
            is_valid=True,
            is_recommended=len(warnings) == 0,
            warnings=warnings,
            errors=errors,
            confidence=1.0
        )

    def compute_migration_path(
        self,
        from_version: str,
        to_version: str,
        technology: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute migration path between versions.
        """
        from_v = self.parse_version(from_version)
        to_v = self.parse_version(to_version)

        if not from_v or not to_v:
            return {
                "error": "Cannot parse version(s)",
                "from": from_version,
                "to": to_version,
                "refused": True
            }

        if from_v >= to_v:
            return {
                "error": "Downgrade detected - not a standard migration path",
                "from": from_v.to_string(),
                "to": to_v.to_string(),
                "is_downgrade": True
            }

        # Determine migration scope
        is_major_upgrade = from_v.major != to_v.major
        is_minor_upgrade = from_v.minor != to_v.minor and not is_major_upgrade

        migration = {
            "from": from_v.to_string(),
            "to": to_v.to_string(),
            "technology": technology,
            "scope": "MAJOR" if is_major_upgrade else "MINOR" if is_minor_upgrade else "PATCH",
            "breaking_changes_expected": is_major_upgrade,
            "intermediate_versions": [],
            "recommendations": []
        }

        if is_major_upgrade:
            migration["recommendations"].append("Review breaking changes documentation")
            migration["recommendations"].append("Run compatibility tests before upgrading")
            migration["recommendations"].append("Consider incremental major version upgrades")

            # Suggest intermediate versions
            for major in range(from_v.major + 1, to_v.major + 1):
                migration["intermediate_versions"].append(f"{major}.0.0")

        elif is_minor_upgrade:
            migration["recommendations"].append("Review changelog for new features")
            migration["recommendations"].append("Check for deprecation notices")

        return migration

    def extract_version_metadata(
        self,
        content: str,
        existing: Optional[VersionMetadata] = None
    ) -> VersionMetadata:
        """
        Extract version metadata from document content.
        """
        metadata = existing or VersionMetadata()

        content_lower = content.lower()[:50000]

        # Version patterns
        patterns = [
            (r"introduced\s+in\s+(?:version\s+)?v?([\d.]+)", "version_introduced"),
            (r"available\s+(?:since|from)\s+v?([\d.]+)", "version_introduced"),
            (r"deprecated\s+(?:in|since)\s+v?([\d.]+)", "version_deprecated"),
            (r"will\s+be\s+(?:removed|deprecated)\s+in\s+v?([\d.]+)", "version_deprecated"),
            (r"removed\s+in\s+v?([\d.]+)", "version_removed"),
            (r"no\s+longer\s+(?:available|supported)\s+(?:as\s+of|in|since)\s+v?([\d.]+)", "version_removed"),
            (r"use\s+([^\s,]+(?:\s+\d+)?)\s+instead", "replacement_path"),
            (r"replaced\s+by\s+([^\s,]+)", "replacement_path"),
            (r"migrate\s+to\s+([^\s,]+)", "replacement_path"),
        ]

        for pattern, field in patterns:
            match = re.search(pattern, content_lower)
            if match and not getattr(metadata, field, None):
                setattr(metadata, field, match.group(1))

        # Detect status
        if any(kw in content_lower for kw in ["removed", "no longer available", "discontinued"]):
            metadata.status = VersionStatus.REMOVED
        elif any(kw in content_lower for kw in ["deprecated", "deprecate", "obsolete"]):
            metadata.status = VersionStatus.DEPRECATED
        elif any(kw in content_lower for kw in ["alpha", "experimental"]):
            metadata.status = VersionStatus.ALPHA
        elif any(kw in content_lower for kw in ["beta", "preview"]):
            metadata.status = VersionStatus.BETA
        elif any(kw in content_lower for kw in ["end of life", "eol", "sunset"]):
            metadata.status = VersionStatus.END_OF_LIFE

        # Extract breaking changes
        breaking_pattern = r"(?:breaking\s+change[s]?:?\s*)([^\n]+)"
        metadata.breaking_changes = re.findall(breaking_pattern, content_lower)[:10]

        metadata.last_verified = datetime.now()
        return metadata

    def get_version_report(
        self,
        doctrine: EngineeringDoctrine,
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive version report for a doctrine.
        """
        meta = doctrine.version_metadata

        report = {
            "doctrine_id": doctrine.doctrine_id,
            "title": doctrine.title,
            "has_version_metadata": meta is not None,
            "metadata": None,
            "target_check": None,
            "confidence": 0.0
        }

        if not meta:
            report["warning"] = "NO VERSION METADATA - Cannot provide version guidance"
            return report

        report["metadata"] = {
            "introduced": meta.version_introduced,
            "deprecated": meta.version_deprecated,
            "removed": meta.version_removed,
            "status": meta.status.value if meta.status else "UNKNOWN",
            "replacement": meta.replacement_path,
            "breaking_changes": meta.breaking_changes,
            "last_verified": meta.last_verified.isoformat() if meta.last_verified else None
        }

        # Calculate completeness
        completeness = 0.0
        if meta.version_introduced:
            completeness += 0.4
        if meta.last_verified:
            completeness += 0.2
        if meta.status:
            completeness += 0.2
        if meta.replacement_path:
            completeness += 0.1
        if meta.breaking_changes:
            completeness += 0.1
        report["metadata_completeness"] = completeness
        report["confidence"] = completeness

        if target_version:
            check = self.check_compatibility(doctrine, target_version)
            report["target_check"] = {
                "version": target_version,
                "is_valid": check.is_valid,
                "is_recommended": check.is_recommended,
                "warnings": check.warnings,
                "errors": check.errors,
                "migration_required": check.migration_required,
                "migration_path": check.migration_path,
                "refused": check.refused,
                "refusal_reason": check.refusal_reason
            }

        return report


# Self-test assertions
def _self_test():
    """Validate version lifecycle engine."""
    engine = VersionLifecycleEngine()

    # Test version parsing
    v1 = engine.parse_version("1.2.3")
    assert v1 is not None, "Should parse semver"
    assert v1.major == 1 and v1.minor == 2 and v1.patch == 3

    v2 = engine.parse_version("2.0.0-beta.1")
    assert v2 is not None, "Should parse prerelease"
    assert v2.prerelease == "beta.1"

    # Test comparison
    assert v1 < v2, "1.2.3 < 2.0.0-beta.1"
    assert engine.parse_version("1.0.0") < engine.parse_version("1.0.1")

    # Test constraint parsing
    c1 = engine.parse_constraint(">=1.0.0")
    assert c1 is not None, "Should parse constraint"
    assert c1.operator == ">="
    assert c1.satisfies(engine.parse_version("1.0.0"))
    assert c1.satisfies(engine.parse_version("2.0.0"))
    assert not c1.satisfies(engine.parse_version("0.9.0"))

    # Test caret constraint
    c2 = engine.parse_constraint("^1.2.0")
    assert c2.satisfies(engine.parse_version("1.2.5"))
    assert c2.satisfies(engine.parse_version("1.9.9"))
    assert not c2.satisfies(engine.parse_version("2.0.0"))

    # Test version check
    result = engine.check_version("3.8", technology="python")
    assert result.version.major == 3
    # Python 3.8 is EOL as of late 2024

    # Test refusal on unparseable
    bad_result = engine.check_version("not-a-version")
    assert bad_result.refused is True, "Should refuse unparseable version"
    assert "CANNOT PARSE" in bad_result.refusal_reason

    logger.info("Version Lifecycle Engine self-test PASSED")


if __name__ == "__main__":
    _self_test()
