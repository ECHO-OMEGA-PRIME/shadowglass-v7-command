"""
PROGRAMMING INTELLIGENCE ENGINE - LAYER 2
Version Awareness Engine

CRITICAL: Most AI coding tools fail here.
Every doctrine must have version metadata attached.

The engine must reason:
"Valid — but deprecated. Use X instead."
or
"Removed in v5. Unsafe for production."

If version data is missing → FLAG UNCERTAINTY.
Never hallucinate compatibility.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import re
import json
from loguru import logger

from ..engine.models import (
    VersionMetadata,
    VersionStatus,
    EngineeringDoctrine,
    ConfidenceTier,
    DriftAlert,
    DriftType
)


@dataclass
class VersionCheckResult:
    """Result of a version compatibility check."""
    is_compatible: bool
    is_optimal: bool
    status: VersionStatus
    message: str
    warnings: List[str] = field(default_factory=list)
    migration_path: Optional[str] = None
    breaking_changes: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class SemanticVersion:
    """Parsed semantic version for comparison."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    raw: str = ""

    def __lt__(self, other: "SemanticVersion") -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # Pre-release versions are less than release versions
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        return False

    def __le__(self, other: "SemanticVersion") -> bool:
        return self == other or self < other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major == other.major and
                self.minor == other.minor and
                self.patch == other.patch and
                self.prerelease == other.prerelease)

    def __gt__(self, other: "SemanticVersion") -> bool:
        return not self <= other

    def __ge__(self, other: "SemanticVersion") -> bool:
        return not self < other


class VersionAwarenessEngine:
    """
    LAYER 2: Version Awareness Engine

    Every doctrine must have version metadata.
    Never hallucinate compatibility.
    Flag uncertainty when version data is missing.
    """

    # Pattern for extracting version numbers
    VERSION_PATTERNS = [
        r"v?(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?",  # Semantic versioning
        r"v?(\d+)\.(\d+)",  # Major.minor only
        r"version\s*(\d+)",  # Single version number
    ]

    # Keywords indicating deprecation
    DEPRECATION_KEYWORDS = [
        "deprecated", "deprecate", "obsolete", "legacy",
        "end of life", "eol", "sunset", "discontinued",
        "no longer supported", "will be removed", "scheduled for removal"
    ]

    # Keywords indicating breaking changes
    BREAKING_KEYWORDS = [
        "breaking change", "breaking:", "!:", "major change",
        "incompatible", "migration required", "must update"
    ]

    def __init__(self):
        self.version_cache: Dict[str, SemanticVersion] = {}
        self.deprecation_registry: Dict[str, VersionMetadata] = {}
        logger.info("Version Awareness Engine initialized")

    def parse_version(self, version_string: str) -> Optional[SemanticVersion]:
        """
        Parse a version string into a SemanticVersion.
        Handles various formats gracefully.
        """
        if not version_string:
            return None

        # Check cache
        if version_string in self.version_cache:
            return self.version_cache[version_string]

        # Try each pattern
        for pattern in self.VERSION_PATTERNS:
            match = re.search(pattern, version_string)
            if match:
                groups = match.groups()
                try:
                    major = int(groups[0])
                    minor = int(groups[1]) if len(groups) > 1 and groups[1] else 0
                    patch = int(groups[2]) if len(groups) > 2 and groups[2] else 0
                    prerelease = groups[3] if len(groups) > 3 else None

                    version = SemanticVersion(
                        major=major,
                        minor=minor,
                        patch=patch,
                        prerelease=prerelease,
                        raw=version_string
                    )
                    self.version_cache[version_string] = version
                    return version
                except (ValueError, IndexError):
                    continue

        logger.warning(f"Unable to parse version: {version_string}")
        return None

    def check_version_compatibility(
        self,
        doctrine: EngineeringDoctrine,
        target_version: str
    ) -> VersionCheckResult:
        """
        Check if a doctrine is compatible with a target version.

        CRITICAL: Never hallucinate compatibility.
        If unsure, return low confidence and flag for review.
        """
        if not doctrine.version_metadata:
            return VersionCheckResult(
                is_compatible=True,
                is_optimal=False,
                status=VersionStatus.ACTIVE,
                message="No version metadata available. Compatibility uncertain.",
                warnings=["Version metadata missing - cannot verify compatibility"],
                confidence=0.3
            )

        meta = doctrine.version_metadata
        target = self.parse_version(target_version)

        if not target:
            return VersionCheckResult(
                is_compatible=True,
                is_optimal=False,
                status=meta.status,
                message=f"Unable to parse target version: {target_version}",
                warnings=["Target version unparseable"],
                confidence=0.5
            )

        # Check if removed
        if meta.version_removed:
            removed = self.parse_version(meta.version_removed)
            if removed and target >= removed:
                return VersionCheckResult(
                    is_compatible=False,
                    is_optimal=False,
                    status=VersionStatus.REMOVED,
                    message=f"REMOVED in {meta.version_removed}. Unsafe for production.",
                    warnings=[f"Feature was removed in version {meta.version_removed}"],
                    migration_path=meta.replacement_path,
                    breaking_changes=meta.breaking_changes,
                    confidence=1.0
                )

        # Check if deprecated
        if meta.version_deprecated:
            deprecated = self.parse_version(meta.version_deprecated)
            if deprecated and target >= deprecated:
                return VersionCheckResult(
                    is_compatible=True,
                    is_optimal=False,
                    status=VersionStatus.DEPRECATED,
                    message=f"DEPRECATED since {meta.version_deprecated}. Consider: {meta.replacement_path or 'See migration guide'}",
                    warnings=[
                        f"Deprecated since {meta.version_deprecated}",
                        "Will be removed in future version"
                    ],
                    migration_path=meta.replacement_path,
                    breaking_changes=meta.breaking_changes,
                    confidence=0.9
                )

        # Check if not yet introduced
        if meta.version_introduced:
            introduced = self.parse_version(meta.version_introduced)
            if introduced and target < introduced:
                return VersionCheckResult(
                    is_compatible=False,
                    is_optimal=False,
                    status=VersionStatus.ACTIVE,
                    message=f"Not available until {meta.version_introduced}",
                    warnings=[f"Feature introduced in {meta.version_introduced}, target is {target_version}"],
                    confidence=1.0
                )

        # Compatible and active
        return VersionCheckResult(
            is_compatible=True,
            is_optimal=True,
            status=VersionStatus.ACTIVE,
            message="Compatible with target version",
            warnings=[],
            compatibility_notes=meta.compatibility_notes if hasattr(meta, 'compatibility_notes') else [],
            confidence=1.0
        )

    def extract_version_metadata(
        self,
        content: str,
        source_metadata: Optional[Dict] = None
    ) -> VersionMetadata:
        """
        Extract version metadata from document content.
        Uses pattern matching and NLP-style extraction.
        """
        metadata = VersionMetadata()

        # Look for explicit version declarations
        version_patterns = [
            (r"introduced\s+in\s+(?:version\s+)?v?([\d.]+)", "version_introduced"),
            (r"available\s+(?:since|from)\s+v?([\d.]+)", "version_introduced"),
            (r"deprecated\s+(?:in|since)\s+v?([\d.]+)", "version_deprecated"),
            (r"will\s+be\s+(?:removed|deprecated)\s+in\s+v?([\d.]+)", "version_deprecated"),
            (r"removed\s+in\s+v?([\d.]+)", "version_removed"),
            (r"no\s+longer\s+available\s+(?:as\s+of|in)\s+v?([\d.]+)", "version_removed"),
            (r"use\s+([^\s,]+)\s+instead", "replacement_path"),
            (r"replaced\s+by\s+([^\s,]+)", "replacement_path"),
            (r"migrate\s+to\s+([^\s,]+)", "replacement_path"),
        ]

        content_lower = content.lower()

        for pattern, field in version_patterns:
            match = re.search(pattern, content_lower)
            if match:
                value = match.group(1)
                setattr(metadata, field, value)

        # Detect status based on keywords
        if any(kw in content_lower for kw in ["removed", "no longer available", "discontinued"]):
            metadata.status = VersionStatus.REMOVED
        elif any(kw in content_lower for kw in self.DEPRECATION_KEYWORDS):
            metadata.status = VersionStatus.DEPRECATED
        elif any(kw in content_lower for kw in ["alpha", "experimental"]):
            metadata.status = VersionStatus.ALPHA
        elif any(kw in content_lower for kw in ["beta", "preview"]):
            metadata.status = VersionStatus.BETA
        elif any(kw in content_lower for kw in ["legacy", "maintenance mode"]):
            metadata.status = VersionStatus.LEGACY
        else:
            metadata.status = VersionStatus.ACTIVE

        # Extract breaking changes
        breaking_pattern = r"(?:breaking\s+change[s]?:?\s*)([^\n]+)"
        breaking_matches = re.findall(breaking_pattern, content_lower)
        metadata.breaking_changes = breaking_matches[:10]  # Limit to 10

        # Extract compatibility notes
        compat_pattern = r"(?:compatibility|note|warning):?\s*([^\n]+)"
        compat_matches = re.findall(compat_pattern, content_lower)
        metadata.compatibility_notes = compat_matches[:10]

        # Use source metadata if available
        if source_metadata:
            if "version" in source_metadata and not metadata.version_introduced:
                metadata.version_introduced = source_metadata["version"]
            if "deprecated" in source_metadata:
                metadata.version_deprecated = source_metadata["deprecated"]
            if "removed" in source_metadata:
                metadata.version_removed = source_metadata["removed"]

        metadata.last_verified = datetime.now()
        return metadata

    def create_migration_advisory(
        self,
        from_version: str,
        to_version: str,
        affected_doctrines: List[EngineeringDoctrine]
    ) -> Dict[str, Any]:
        """
        Create a migration advisory for version upgrade.
        Lists all breaking changes and deprecations.
        """
        from_v = self.parse_version(from_version)
        to_v = self.parse_version(to_version)

        if not from_v or not to_v:
            return {
                "error": "Unable to parse version(s)",
                "from": from_version,
                "to": to_version
            }

        breaking_changes = []
        deprecations = []
        removals = []
        migrations_required = []

        for doctrine in affected_doctrines:
            if not doctrine.version_metadata:
                continue

            meta = doctrine.version_metadata
            check = self.check_version_compatibility(doctrine, to_version)

            if check.status == VersionStatus.REMOVED:
                removals.append({
                    "doctrine_id": doctrine.doctrine_id,
                    "title": doctrine.title,
                    "removed_in": meta.version_removed,
                    "replacement": meta.replacement_path
                })
            elif check.status == VersionStatus.DEPRECATED:
                deprecations.append({
                    "doctrine_id": doctrine.doctrine_id,
                    "title": doctrine.title,
                    "deprecated_in": meta.version_deprecated,
                    "replacement": meta.replacement_path
                })

            if meta.breaking_changes:
                for change in meta.breaking_changes:
                    breaking_changes.append({
                        "doctrine_id": doctrine.doctrine_id,
                        "change": change
                    })

            if check.migration_path:
                migrations_required.append({
                    "doctrine_id": doctrine.doctrine_id,
                    "from": doctrine.title,
                    "to": check.migration_path
                })

        return {
            "migration_advisory": {
                "from_version": from_version,
                "to_version": to_version,
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_affected": len(affected_doctrines),
                    "removals": len(removals),
                    "deprecations": len(deprecations),
                    "breaking_changes": len(breaking_changes),
                    "migrations_required": len(migrations_required)
                },
                "removals": removals,
                "deprecations": deprecations,
                "breaking_changes": breaking_changes,
                "migrations_required": migrations_required,
                "recommendation": self._generate_migration_recommendation(
                    removals, deprecations, breaking_changes
                )
            }
        }

    def _generate_migration_recommendation(
        self,
        removals: List,
        deprecations: List,
        breaking_changes: List
    ) -> str:
        """Generate a recommendation for the migration."""
        if removals:
            return "CRITICAL: Removed features detected. Migration required before upgrade."
        if breaking_changes:
            return "WARNING: Breaking changes detected. Review and update affected code."
        if deprecations:
            return "NOTICE: Deprecations detected. Plan migration to replacements."
        return "SAFE: No compatibility issues detected for this upgrade."

    def detect_drift(
        self,
        doctrine: EngineeringDoctrine,
        current_source_content: str
    ) -> Optional[DriftAlert]:
        """
        Detect if a doctrine has drifted from its source.
        Compares stored metadata against current source content.
        """
        new_metadata = self.extract_version_metadata(current_source_content)

        if not doctrine.version_metadata:
            return None

        old = doctrine.version_metadata
        new = new_metadata

        # Check for deprecation announcement
        if old.status == VersionStatus.ACTIVE and new.status == VersionStatus.DEPRECATED:
            return DriftAlert(
                alert_id=f"drift_{doctrine.doctrine_id}_{datetime.now().timestamp()}",
                drift_type=DriftType.DEPRECATION,
                affected_doctrines=[doctrine.doctrine_id],
                severity="HIGH",
                description=f"Deprecation detected: {doctrine.title}",
                migration_path=new.replacement_path,
                source_trigger="version_check"
            )

        # Check for removal
        if old.status != VersionStatus.REMOVED and new.status == VersionStatus.REMOVED:
            return DriftAlert(
                alert_id=f"drift_{doctrine.doctrine_id}_{datetime.now().timestamp()}",
                drift_type=DriftType.API_REMOVAL,
                affected_doctrines=[doctrine.doctrine_id],
                severity="CRITICAL",
                description=f"API/Feature removed: {doctrine.title}",
                migration_path=new.replacement_path,
                source_trigger="version_check"
            )

        # Check for new breaking changes
        new_breaking = set(new.breaking_changes) - set(old.breaking_changes)
        if new_breaking:
            return DriftAlert(
                alert_id=f"drift_{doctrine.doctrine_id}_{datetime.now().timestamp()}",
                drift_type=DriftType.BREAKING_CHANGE,
                affected_doctrines=[doctrine.doctrine_id],
                severity="HIGH",
                description=f"New breaking changes in {doctrine.title}: {list(new_breaking)[:3]}",
                source_trigger="version_check"
            )

        return None

    def get_version_report(
        self,
        doctrine: EngineeringDoctrine,
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive version report for a doctrine."""
        meta = doctrine.version_metadata

        report = {
            "doctrine_id": doctrine.doctrine_id,
            "title": doctrine.title,
            "version_metadata": {
                "introduced": meta.version_introduced if meta else None,
                "deprecated": meta.version_deprecated if meta else None,
                "removed": meta.version_removed if meta else None,
                "status": meta.status.value if meta else "UNKNOWN",
                "replacement": meta.replacement_path if meta else None,
                "breaking_changes": meta.breaking_changes if meta else [],
                "last_verified": meta.last_verified.isoformat() if meta and meta.last_verified else None
            },
            "metadata_completeness": self._calculate_metadata_completeness(meta),
            "version_warnings": []
        }

        if target_version:
            check = self.check_version_compatibility(doctrine, target_version)
            report["target_compatibility"] = {
                "version": target_version,
                "compatible": check.is_compatible,
                "optimal": check.is_optimal,
                "status": check.status.value,
                "message": check.message,
                "warnings": check.warnings,
                "confidence": check.confidence
            }

        return report

    def _calculate_metadata_completeness(self, meta: Optional[VersionMetadata]) -> float:
        """Calculate how complete the version metadata is."""
        if not meta:
            return 0.0

        fields = [
            meta.version_introduced,
            meta.version_deprecated,
            meta.version_removed,
            meta.replacement_path,
            meta.breaking_changes,
            meta.last_verified
        ]

        # version_introduced is most important
        score = 0.0
        if meta.version_introduced:
            score += 0.4
        if meta.last_verified:
            score += 0.2
        if meta.status != VersionStatus.ACTIVE or meta.version_deprecated or meta.version_removed:
            score += 0.2  # Having lifecycle info
        if meta.replacement_path:
            score += 0.1
        if meta.breaking_changes:
            score += 0.1

        return min(score, 1.0)
