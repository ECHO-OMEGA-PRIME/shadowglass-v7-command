"""
PROGRAMMING INTELLIGENCE ENGINE - Authority Classification Engine
ENHANCED SOURCE CATEGORIZATION

Extends basic vendor classification with institutional source typing.
Integrates with AuthorityRegistry for immutable classifications.

Source Categories (from institutional epistemology):
1. SPEC - Specifications are ground truth
2. VENDOR_DOCS - Official vendor documentation
3. RUNTIME_REALITY - Observed behavior trumps docs when they conflict
4. DEPRECATION_NOTICE - Authoritative lifecycle announcements
5. REFERENCE_IMPL - Canonical implementations
6. FAILURE_NARRATIVE - Postmortems, CVEs, incident reports

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from pathlib import Path
import hashlib
import re
from loguru import logger

from ..registry.authority_registry import (
    AuthorityRegistry,
    AuthorityRecord,
    SourceType,
    SourceTypeWeight,
    ClassificationEvidence
)
from ..engine.models import (
    AuthorityTier,
    TrustLevel,
    SourceReference,
    EngineeringDoctrine
)


@dataclass
class ClassificationResult:
    """
    Complete classification result combining type and tier.
    Represents PIE's full understanding of a source's authority.
    """
    source_id: str
    source_type: SourceType
    authority_tier: AuthorityTier
    trust_level: TrustLevel
    combined_weight: int
    vendor: Optional[str]
    evidence: List[str]
    confidence: float
    classification_time: datetime = field(default_factory=datetime.now)

    # Epistemological metadata
    can_contradict_docs: bool = False      # Runtime reality can contradict
    lifecycle_authoritative: bool = False   # Deprecation notices are authoritative
    requires_version_context: bool = True   # Most sources need version awareness

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "authority_tier": self.authority_tier.name,
            "trust_level": self.trust_level.value,
            "combined_weight": self.combined_weight,
            "vendor": self.vendor,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "epistemology": {
                "can_contradict_docs": self.can_contradict_docs,
                "lifecycle_authoritative": self.lifecycle_authoritative,
                "requires_version_context": self.requires_version_context
            }
        }


class AuthorityClassificationEngine:
    """
    ENHANCED AUTHORITY CLASSIFICATION ENGINE

    Combines source TYPE classification with vendor TIER classification.
    Produces epistemologically-aware authority assessments.

    Key capabilities:
    - Classify sources by institutional type (SPEC, VENDOR_DOCS, etc.)
    - Assign authority tiers (PRIMARY, CANONICAL, STRUCTURED, etc.)
    - Detect epistemological properties (can contradict docs, lifecycle authority)
    - Resolve conflicts deterministically
    """

    # Mapping from SourceType to base AuthorityTier
    TYPE_TO_TIER: Dict[SourceType, AuthorityTier] = {
        SourceType.SPEC: AuthorityTier.STRUCTURED_TECHNICAL,
        SourceType.VENDOR_DOCS: AuthorityTier.PRIMARY_SOURCE,
        SourceType.RUNTIME_REALITY: AuthorityTier.VERIFIED_EXPERT,
        SourceType.DEPRECATION_NOTICE: AuthorityTier.PRIMARY_SOURCE,
        SourceType.REFERENCE_IMPL: AuthorityTier.CANONICAL_ENGINEERING,
        SourceType.FAILURE_NARRATIVE: AuthorityTier.STRUCTURED_TECHNICAL,
        SourceType.API_DEFINITION: AuthorityTier.PRIMARY_SOURCE,
        SourceType.CHANGELOG: AuthorityTier.CANONICAL_ENGINEERING,
        SourceType.TUTORIAL: AuthorityTier.VERIFIED_EXPERT,
        SourceType.COMMUNITY: AuthorityTier.COMMUNITY_KNOWLEDGE,
    }

    # Mapping from SourceType to TrustLevel
    TYPE_TO_TRUST: Dict[SourceType, TrustLevel] = {
        SourceType.SPEC: TrustLevel.FORMAL,
        SourceType.VENDOR_DOCS: TrustLevel.ABSOLUTE,
        SourceType.RUNTIME_REALITY: TrustLevel.VERIFIED,
        SourceType.DEPRECATION_NOTICE: TrustLevel.ABSOLUTE,
        SourceType.REFERENCE_IMPL: TrustLevel.HIGH,
        SourceType.FAILURE_NARRATIVE: TrustLevel.VERIFIED,
        SourceType.API_DEFINITION: TrustLevel.ABSOLUTE,
        SourceType.CHANGELOG: TrustLevel.HIGH,
        SourceType.TUTORIAL: TrustLevel.HIGH,
        SourceType.COMMUNITY: TrustLevel.COMMUNITY,
    }

    def __init__(
        self,
        registry: Optional[AuthorityRegistry] = None,
        persist_path: Optional[Path] = None
    ):
        self.registry = registry or AuthorityRegistry(persist_path)
        self._classification_cache: Dict[str, ClassificationResult] = {}

        logger.info("Authority Classification Engine initialized")

    def classify(
        self,
        source_id: str,
        content: str,
        url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ClassificationResult:
        """
        Fully classify a source with type, tier, trust, and epistemology.

        This is the primary classification method. Use this for all new sources.

        Args:
            source_id: Unique identifier for the source
            content: Full content of the source document
            url: Optional URL of the source
            metadata: Optional metadata (vendor, version, etc.)

        Returns:
            ClassificationResult with complete authority assessment
        """
        # Check cache
        cache_key = f"{source_id}_{hashlib.sha256(content.encode()).hexdigest()[:8]}"
        if cache_key in self._classification_cache:
            return self._classification_cache[cache_key]

        # Get immutable registry classification
        record = self.registry.classify_source(
            source_id=source_id,
            content=content,
            url=url,
            metadata=metadata
        )

        # Build full classification result
        result = self._build_classification_result(record, content, metadata)

        # Cache it
        self._classification_cache[cache_key] = result

        return result

    def _build_classification_result(
        self,
        record: AuthorityRecord,
        content: str,
        metadata: Optional[Dict]
    ) -> ClassificationResult:
        """Build complete classification result from registry record."""

        source_type = record.source_type
        authority_tier = self._determine_authority_tier(source_type, record.vendor)
        trust_level = self.TYPE_TO_TRUST.get(source_type, TrustLevel.COMMUNITY)

        # Compute combined weight
        combined_weight = record.authority_weight

        # Boost for vendor docs from primary vendors
        primary_vendors = {"google", "apple", "microsoft", "amazon", "python", "rust"}
        if record.vendor in primary_vendors and source_type == SourceType.VENDOR_DOCS:
            combined_weight += 10

        # Epistemological properties
        can_contradict_docs = source_type == SourceType.RUNTIME_REALITY
        lifecycle_authoritative = source_type in {
            SourceType.DEPRECATION_NOTICE,
            SourceType.CHANGELOG
        }
        requires_version_context = source_type not in {
            SourceType.SPEC,  # Specs are versioned internally
            SourceType.FAILURE_NARRATIVE  # Postmortems are point-in-time
        }

        # Calculate confidence
        confidence = self._calculate_confidence(record, content)

        return ClassificationResult(
            source_id=record.source_id,
            source_type=source_type,
            authority_tier=authority_tier,
            trust_level=trust_level,
            combined_weight=combined_weight,
            vendor=record.vendor,
            evidence=list(record.evidence),
            confidence=confidence,
            can_contradict_docs=can_contradict_docs,
            lifecycle_authoritative=lifecycle_authoritative,
            requires_version_context=requires_version_context
        )

    def _determine_authority_tier(
        self,
        source_type: SourceType,
        vendor: Optional[str]
    ) -> AuthorityTier:
        """Determine authority tier from type and vendor."""
        base_tier = self.TYPE_TO_TIER.get(source_type, AuthorityTier.COMMUNITY_KNOWLEDGE)

        # Vendor can elevate tier
        if vendor:
            primary_vendors = {"google", "apple", "microsoft", "amazon"}
            if vendor in primary_vendors:
                if base_tier.value < AuthorityTier.PRIMARY_SOURCE.value:
                    return AuthorityTier.PRIMARY_SOURCE
            elif vendor in {"kubernetes", "docker", "terraform", "github"}:
                if base_tier.value < AuthorityTier.CANONICAL_ENGINEERING.value:
                    return AuthorityTier.CANONICAL_ENGINEERING

        return base_tier

    def _calculate_confidence(
        self,
        record: AuthorityRecord,
        content: str
    ) -> float:
        """Calculate classification confidence."""
        confidence = 0.5  # Base

        # Evidence count boost
        evidence_count = len(record.evidence)
        confidence += min(evidence_count * 0.1, 0.3)

        # Vendor identification boost
        if record.vendor:
            confidence += 0.15

        # Content length boost (more content = more patterns)
        if len(content) > 5000:
            confidence += 0.05

        return min(confidence, 1.0)

    def classify_multiple(
        self,
        sources: List[Tuple[str, str, Optional[str]]]
    ) -> Dict[str, ClassificationResult]:
        """
        Classify multiple sources efficiently.

        Args:
            sources: List of (source_id, content, url) tuples

        Returns:
            Dict mapping source_id to ClassificationResult
        """
        results = {}
        for source_id, content, url in sources:
            results[source_id] = self.classify(source_id, content, url)
        return results

    def resolve_authority_conflict(
        self,
        classifications: List[ClassificationResult]
    ) -> Tuple[ClassificationResult, Dict[str, Any]]:
        """
        Resolve conflict between multiple classifications.

        DETERMINISTIC RULES:
        1. Higher combined_weight wins
        2. Tie: SPEC > VENDOR_DOCS > API_DEFINITION > others
        3. Tie: Higher confidence wins
        4. Tie: More recent classification wins

        Args:
            classifications: List of competing classifications

        Returns:
            (winner, resolution_report)
        """
        if not classifications:
            raise ValueError("No classifications to resolve")

        if len(classifications) == 1:
            return classifications[0], {"conflict": False}

        # Sort by combined weight descending
        sorted_cls = sorted(
            classifications,
            key=lambda c: (c.combined_weight, c.confidence),
            reverse=True
        )

        winner = sorted_cls[0]
        losers = sorted_cls[1:]

        # Check for tie at top
        if sorted_cls[0].combined_weight == sorted_cls[1].combined_weight:
            # Apply type priority
            type_priority = [
                SourceType.SPEC,
                SourceType.VENDOR_DOCS,
                SourceType.API_DEFINITION,
                SourceType.DEPRECATION_NOTICE,
                SourceType.REFERENCE_IMPL,
            ]
            for priority_type in type_priority:
                for cls in sorted_cls:
                    if cls.source_type == priority_type:
                        winner = cls
                        break
                if winner != sorted_cls[0]:
                    break

        resolution = {
            "conflict": True,
            "resolution_method": "HIGHER_AUTHORITY_WINS",
            "winner": winner.to_dict(),
            "defeated_count": len(losers),
            "defeated": [
                {
                    "source_id": c.source_id,
                    "source_type": c.source_type.value,
                    "combined_weight": c.combined_weight,
                    "reason": f"Lower authority ({c.combined_weight} < {winner.combined_weight})"
                }
                for c in losers
            ]
        }

        return winner, resolution

    def get_epistemological_assessment(
        self,
        classification: ClassificationResult
    ) -> Dict[str, Any]:
        """
        Get detailed epistemological assessment for a classification.

        Explains WHY this source has authority and WHEN to trust it.
        """
        assessment = {
            "source_id": classification.source_id,
            "epistemology": {
                "authority_basis": self._get_authority_basis(classification),
                "trust_conditions": self._get_trust_conditions(classification),
                "contradiction_policy": self._get_contradiction_policy(classification),
                "temporal_validity": self._get_temporal_validity(classification),
                "known_limitations": self._get_limitations(classification)
            }
        }
        return assessment

    def _get_authority_basis(self, cls: ClassificationResult) -> str:
        """Explain why this source has authority."""
        bases = {
            SourceType.SPEC: "Formal specification from standards body. Defines normative behavior.",
            SourceType.VENDOR_DOCS: f"Official documentation from {cls.vendor or 'vendor'}. Defines intended behavior.",
            SourceType.RUNTIME_REALITY: "Observed behavior from production systems. Shows actual behavior.",
            SourceType.DEPRECATION_NOTICE: "Official lifecycle announcement. Authoritative for deprecation status.",
            SourceType.REFERENCE_IMPL: "Canonical implementation from maintainers. Demonstrates correct usage.",
            SourceType.FAILURE_NARRATIVE: "Post-incident analysis. Reveals failure modes not in documentation.",
            SourceType.API_DEFINITION: "Formal API contract. Defines interface boundaries.",
            SourceType.CHANGELOG: "Official change record. Authoritative for version changes.",
            SourceType.TUTORIAL: "Official learning material. May be simplified or outdated.",
            SourceType.COMMUNITY: "Community-contributed content. Requires additional verification.",
        }
        return bases.get(cls.source_type, "Unknown authority basis")

    def _get_trust_conditions(self, cls: ClassificationResult) -> List[str]:
        """List conditions under which this source should be trusted."""
        conditions = []

        if cls.source_type == SourceType.SPEC:
            conditions.append("Trust when implementing to specification")
            conditions.append("Verify version matches target specification")
        elif cls.source_type == SourceType.VENDOR_DOCS:
            conditions.append("Trust for intended behavior and official APIs")
            conditions.append("Verify documentation version matches your SDK version")
        elif cls.source_type == SourceType.RUNTIME_REALITY:
            conditions.append("Trust when docs and reality conflict")
            conditions.append("Document as 'undocumented behavior' - may change")
        elif cls.source_type == SourceType.DEPRECATION_NOTICE:
            conditions.append("Trust for lifecycle status")
            conditions.append("Use for migration planning")
        elif cls.source_type == SourceType.FAILURE_NARRATIVE:
            conditions.append("Trust for failure mode understanding")
            conditions.append("May not apply to different configurations")

        if cls.requires_version_context:
            conditions.append("REQUIRES VERSION CONTEXT - verify version before trusting")

        return conditions

    def _get_contradiction_policy(self, cls: ClassificationResult) -> str:
        """Policy for when this source contradicts others."""
        if cls.source_type == SourceType.RUNTIME_REALITY:
            return "MAY CONTRADICT DOCS: If observed behavior differs from documentation, this source takes precedence for understanding actual behavior."
        elif cls.source_type == SourceType.DEPRECATION_NOTICE:
            return "SUPERSEDES PRIOR DOCS: Deprecation notices update the lifecycle status regardless of what older docs say."
        elif cls.source_type == SourceType.SPEC:
            return "DOES NOT CONTRADICT: Specifications define normative behavior. Implementation may differ."
        else:
            return "DEFER TO HIGHER AUTHORITY: When in conflict, defer to sources with higher authority weight."

    def _get_temporal_validity(self, cls: ClassificationResult) -> str:
        """Temporal validity assessment."""
        if cls.source_type == SourceType.SPEC:
            return "STABLE: Specifications rarely change after finalization."
        elif cls.source_type in {SourceType.VENDOR_DOCS, SourceType.API_DEFINITION}:
            return "VERSION-BOUND: Valid for specific versions. Must verify version match."
        elif cls.source_type == SourceType.FAILURE_NARRATIVE:
            return "POINT-IN-TIME: Represents state at time of incident. May not reflect current behavior."
        elif cls.source_type == SourceType.CHANGELOG:
            return "CUMULATIVE: Adds to prior knowledge. Does not invalidate older entries."
        else:
            return "VOLATILE: May become outdated. Verify currency before using."

    def _get_limitations(self, cls: ClassificationResult) -> List[str]:
        """Known limitations of this source type."""
        limitations = []

        if cls.source_type == SourceType.COMMUNITY:
            limitations.append("May contain errors or outdated information")
            limitations.append("Requires verification against official sources")
        if cls.source_type == SourceType.TUTORIAL:
            limitations.append("May be simplified for learning purposes")
            limitations.append("May not cover edge cases")
        if cls.source_type == SourceType.RUNTIME_REALITY:
            limitations.append("Behavior may change without notice")
            limitations.append("May be environment-specific")
        if cls.confidence < 0.7:
            limitations.append(f"Low classification confidence ({cls.confidence:.2f})")

        return limitations

    def create_source_reference(
        self,
        classification: ClassificationResult,
        url: Optional[str] = None,
        file_path: Optional[Path] = None,
        content: Optional[str] = None
    ) -> SourceReference:
        """Create a SourceReference from a classification."""
        ref = SourceReference(
            source_id=classification.source_id,
            source_type=classification.source_type.value,
            authority_tier=classification.authority_tier,
            trust_level=classification.trust_level,
            url=url,
            file_path=file_path,
            last_accessed=datetime.now(),
            vendor=classification.vendor
        )
        if content:
            ref.compute_content_hash(content)
        return ref

    def get_statistics(self) -> Dict[str, Any]:
        """Get classification engine statistics."""
        return {
            "cached_classifications": len(self._classification_cache),
            "registry_stats": self.registry.get_statistics()
        }


# Self-test assertions
def _self_test():
    """Validate classification engine functionality."""
    engine = AuthorityClassificationEngine()

    # Test SPEC classification
    spec_content = """
    RFC 2119: Key words for use in RFCs to Indicate Requirement Levels

    MUST: This word means that the definition is an absolute requirement.
    SHOULD: This word means that there may exist valid reasons to ignore.
    """
    spec_cls = engine.classify("test_rfc_2119", spec_content)
    assert spec_cls.source_type == SourceType.SPEC, "Should classify as SPEC"
    assert spec_cls.authority_tier == AuthorityTier.STRUCTURED_TECHNICAL, "RFC should be STRUCTURED_TECHNICAL"

    # Test vendor docs
    vendor_content = "Firebase Authentication provides backend services to authenticate users."
    vendor_cls = engine.classify(
        "test_firebase",
        vendor_content,
        url="https://firebase.google.com/docs/auth"
    )
    assert vendor_cls.vendor == "google", "Should detect Google vendor"
    assert vendor_cls.authority_tier == AuthorityTier.PRIMARY_SOURCE, "Vendor docs should be PRIMARY"

    # Test deprecation
    dep_content = "This method is deprecated since v2.0 and will be removed in v3.0. Use newMethod() instead."
    dep_cls = engine.classify("test_deprecation", dep_content)
    assert dep_cls.source_type == SourceType.DEPRECATION_NOTICE, "Should detect deprecation"
    assert dep_cls.lifecycle_authoritative is True, "Deprecation should be lifecycle authoritative"

    # Test conflict resolution
    winner, resolution = engine.resolve_authority_conflict([spec_cls, vendor_cls, dep_cls])
    assert winner.combined_weight >= dep_cls.combined_weight, "Winner should have highest weight"
    assert resolution["conflict"] is True, "Should detect conflict"

    # Test epistemological assessment
    assessment = engine.get_epistemological_assessment(spec_cls)
    assert "authority_basis" in assessment["epistemology"], "Should have authority basis"
    assert "trust_conditions" in assessment["epistemology"], "Should have trust conditions"

    logger.info("Authority Classification Engine self-test PASSED")


if __name__ == "__main__":
    _self_test()
