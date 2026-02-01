"""
PROGRAMMING INTELLIGENCE ENGINE - Engineering Judgment Formatter
STRUCTURED DETERMINISTIC OUTPUT

Every engineering judgment from PIE must be formatted with:
1. CLAIM - What is being asserted
2. EVIDENCE - Sources supporting the claim
3. AUTHORITY TIER - Weight of the evidence
4. CONFIDENCE - How certain is this judgment
5. KNOWN UNKNOWNS - What we explicitly don't know
6. REFUSAL CONDITIONS - When this judgment should not be trusted

This produces defensible engineering decisions, not chatbot responses.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import hashlib
import json
from loguru import logger

from ..engine.models import (
    AuthorityTier,
    TrustLevel,
    ConfidenceTier,
    VersionStatus,
    EngineeringDoctrine,
    SourceReference
)
from ..analyzers.authority_classifier import ClassificationResult


class JudgmentType(str, Enum):
    """Types of engineering judgments."""
    RECOMMENDATION = "RECOMMENDATION"     # Suggests an approach
    WARNING = "WARNING"                   # Cautions against something
    ASSERTION = "ASSERTION"               # States a fact
    REFUSAL = "REFUSAL"                   # Refuses to answer
    COMPARISON = "COMPARISON"             # Compares alternatives
    MIGRATION = "MIGRATION"               # Suggests migration path
    COMPATIBILITY = "COMPATIBILITY"       # Compatibility assessment


class RefusalReason(str, Enum):
    """Standard reasons for refusing to provide judgment."""
    MISSING_VERSION = "MISSING_VERSION"           # Version info required
    AMBIGUOUS_CONTEXT = "AMBIGUOUS_CONTEXT"       # Need more context
    CONFLICTING_SOURCES = "CONFLICTING_SOURCES"   # Unresolved conflicts
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Not enough data
    DEPRECATED_TECHNOLOGY = "DEPRECATED_TECHNOLOGY"  # Tech is obsolete
    SECURITY_CONCERN = "SECURITY_CONCERN"         # Security implications
    OUT_OF_SCOPE = "OUT_OF_SCOPE"                 # Beyond PIE's domain


@dataclass
class EvidenceItem:
    """A single piece of evidence supporting a judgment."""
    source_id: str
    source_type: str
    authority_tier: AuthorityTier
    trust_level: TrustLevel
    excerpt: Optional[str]
    relevance_score: float           # 0.0 to 1.0
    version_context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "authority_tier": self.authority_tier.name,
            "trust_level": self.trust_level.value,
            "excerpt": self.excerpt[:200] if self.excerpt else None,
            "relevance_score": self.relevance_score,
            "version_context": self.version_context
        }


@dataclass
class KnownUnknown:
    """An explicitly documented gap in knowledge."""
    area: str                        # What domain the unknown is in
    description: str                 # What we don't know
    impact: str                      # How this affects the judgment
    resolution_path: Optional[str] = None  # How to resolve this


@dataclass
class RefusalCondition:
    """Condition under which this judgment should not be trusted."""
    condition: str
    reason: RefusalReason
    applies_when: str
    alternative_guidance: Optional[str] = None


@dataclass
class EngineeringJudgment:
    """
    A complete, defensible engineering judgment.
    The primary output format of PIE.
    """
    # Identity
    judgment_id: str
    generated_at: datetime
    judgment_type: JudgmentType

    # Core content
    claim: str                       # The assertion being made
    summary: str                     # Brief summary for quick reading
    detailed_reasoning: str          # Full reasoning chain

    # Evidence
    evidence: List[EvidenceItem]
    controlling_evidence: Optional[EvidenceItem]  # Highest authority evidence
    evidence_quality: str            # STRONG, MODERATE, WEAK

    # Authority assessment
    authority_tier: AuthorityTier
    combined_authority_weight: int
    trust_level: TrustLevel

    # Confidence
    confidence_tier: ConfidenceTier
    confidence_score: float          # 0.0 to 1.0
    confidence_reasoning: str

    # Known limitations
    known_unknowns: List[KnownUnknown]
    assumptions: List[str]
    caveats: List[str]

    # Refusal conditions
    refusal_conditions: List[RefusalCondition]
    is_refusal: bool = False
    refusal_reason: Optional[RefusalReason] = None
    refusal_explanation: Optional[str] = None

    # Versioning
    version_context: Optional[str] = None
    version_warnings: List[str] = field(default_factory=list)

    # Determinism
    determinism_hash: Optional[str] = None

    def compute_determinism_hash(self) -> str:
        """Compute hash for identical-input verification."""
        hash_input = json.dumps({
            "claim": self.claim,
            "evidence_ids": [e.source_id for e in self.evidence],
            "authority_weight": self.combined_authority_weight,
            "confidence_score": self.confidence_score,
        }, sort_keys=True)
        self.determinism_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        return self.determinism_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judgment_id": self.judgment_id,
            "generated_at": self.generated_at.isoformat(),
            "judgment_type": self.judgment_type.value,
            "claim": self.claim,
            "summary": self.summary,
            "detailed_reasoning": self.detailed_reasoning,
            "evidence": [e.to_dict() for e in self.evidence],
            "controlling_evidence": self.controlling_evidence.to_dict() if self.controlling_evidence else None,
            "evidence_quality": self.evidence_quality,
            "authority": {
                "tier": self.authority_tier.name,
                "weight": self.combined_authority_weight,
                "trust_level": self.trust_level.value
            },
            "confidence": {
                "tier": self.confidence_tier.value,
                "score": self.confidence_score,
                "reasoning": self.confidence_reasoning
            },
            "known_unknowns": [
                {"area": ku.area, "description": ku.description, "impact": ku.impact}
                for ku in self.known_unknowns
            ],
            "assumptions": self.assumptions,
            "caveats": self.caveats,
            "refusal_conditions": [
                {"condition": rc.condition, "reason": rc.reason.value, "applies_when": rc.applies_when}
                for rc in self.refusal_conditions
            ],
            "is_refusal": self.is_refusal,
            "refusal": {
                "reason": self.refusal_reason.value if self.refusal_reason else None,
                "explanation": self.refusal_explanation
            } if self.is_refusal else None,
            "version_context": self.version_context,
            "version_warnings": self.version_warnings,
            "determinism_hash": self.determinism_hash
        }

    def to_brief(self) -> str:
        """Generate brief human-readable output."""
        lines = [
            f"JUDGMENT: {self.judgment_type.value}",
            f"CLAIM: {self.claim}",
            f"CONFIDENCE: {self.confidence_tier.value} ({self.confidence_score:.0%})",
            f"AUTHORITY: {self.authority_tier.name} (weight: {self.combined_authority_weight})",
        ]

        if self.is_refusal:
            lines.insert(0, f"⚠️ REFUSAL: {self.refusal_explanation}")

        if self.version_warnings:
            lines.append(f"VERSION WARNINGS: {'; '.join(self.version_warnings[:2])}")

        if self.known_unknowns:
            lines.append(f"KNOWN UNKNOWNS: {len(self.known_unknowns)} item(s)")

        if self.caveats:
            lines.append(f"CAVEATS: {'; '.join(self.caveats[:2])}")

        return "\n".join(lines)


class EngineeringJudgmentFormatter:
    """
    ENGINEERING JUDGMENT FORMATTER

    Transforms raw PIE analysis into structured, defensible judgments.
    Every output follows the standard format:
    - Claim
    - Evidence
    - Authority
    - Confidence
    - Known Unknowns
    - Refusal Conditions
    """

    def __init__(self):
        self._judgment_cache: Dict[str, EngineeringJudgment] = {}
        logger.info("Engineering Judgment Formatter initialized")

    def create_judgment(
        self,
        claim: str,
        judgment_type: JudgmentType,
        doctrines: List[EngineeringDoctrine],
        additional_context: Optional[Dict] = None
    ) -> EngineeringJudgment:
        """
        Create a complete engineering judgment from doctrines.
        """
        judgment_id = f"judgment_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.sha256(claim.encode()).hexdigest()[:8]}"

        # Build evidence from doctrines
        evidence = self._build_evidence(doctrines)

        # Find controlling evidence
        controlling = self._find_controlling_evidence(evidence)

        # Assess evidence quality
        evidence_quality = self._assess_evidence_quality(evidence)

        # Calculate authority
        authority_tier = self._determine_authority_tier(evidence)
        combined_weight = sum(e.authority_tier.value for e in evidence)

        # Calculate confidence
        confidence_tier, confidence_score, confidence_reasoning = self._calculate_confidence(
            evidence, evidence_quality, doctrines
        )

        # Identify known unknowns
        known_unknowns = self._identify_known_unknowns(doctrines, additional_context)

        # Identify assumptions
        assumptions = self._identify_assumptions(doctrines, claim)

        # Generate caveats
        caveats = self._generate_caveats(doctrines, evidence)

        # Define refusal conditions
        refusal_conditions = self._define_refusal_conditions(doctrines)

        # Check for version context
        version_context, version_warnings = self._check_version_context(doctrines)

        # Build detailed reasoning
        detailed_reasoning = self._build_reasoning(
            claim, evidence, controlling, doctrines
        )

        # Build summary
        summary = self._build_summary(claim, confidence_tier, authority_tier)

        judgment = EngineeringJudgment(
            judgment_id=judgment_id,
            generated_at=datetime.now(),
            judgment_type=judgment_type,
            claim=claim,
            summary=summary,
            detailed_reasoning=detailed_reasoning,
            evidence=evidence,
            controlling_evidence=controlling,
            evidence_quality=evidence_quality,
            authority_tier=authority_tier,
            combined_authority_weight=combined_weight,
            trust_level=controlling.trust_level if controlling else TrustLevel.COMMUNITY,
            confidence_tier=confidence_tier,
            confidence_score=confidence_score,
            confidence_reasoning=confidence_reasoning,
            known_unknowns=known_unknowns,
            assumptions=assumptions,
            caveats=caveats,
            refusal_conditions=refusal_conditions,
            version_context=version_context,
            version_warnings=version_warnings
        )

        judgment.compute_determinism_hash()
        self._judgment_cache[judgment_id] = judgment

        return judgment

    def create_refusal(
        self,
        reason: RefusalReason,
        explanation: str,
        original_query: str,
        what_would_help: Optional[List[str]] = None
    ) -> EngineeringJudgment:
        """
        Create a judgment that explicitly refuses to answer.
        """
        judgment_id = f"refusal_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        judgment = EngineeringJudgment(
            judgment_id=judgment_id,
            generated_at=datetime.now(),
            judgment_type=JudgmentType.REFUSAL,
            claim=f"REFUSED: Cannot provide judgment for '{original_query}'",
            summary=f"Judgment refused: {reason.value}",
            detailed_reasoning=explanation,
            evidence=[],
            controlling_evidence=None,
            evidence_quality="NONE",
            authority_tier=AuthorityTier.COMMUNITY_KNOWLEDGE,
            combined_authority_weight=0,
            trust_level=TrustLevel.COMMUNITY,
            confidence_tier=ConfidenceTier.REQUIRES_REVIEW,
            confidence_score=0.0,
            confidence_reasoning="Refused to provide judgment due to insufficient information or safety concerns",
            known_unknowns=[KnownUnknown(
                area="Query Context",
                description="Insufficient information to make a determination",
                impact="Cannot provide reliable engineering guidance",
                resolution_path="; ".join(what_would_help) if what_would_help else None
            )],
            assumptions=[],
            caveats=["This is a refusal, not a judgment"],
            refusal_conditions=[],
            is_refusal=True,
            refusal_reason=reason,
            refusal_explanation=explanation
        )

        return judgment

    def _build_evidence(self, doctrines: List[EngineeringDoctrine]) -> List[EvidenceItem]:
        """Build evidence list from doctrines."""
        evidence = []

        for doctrine in doctrines:
            for source in doctrine.source_references:
                evidence.append(EvidenceItem(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    authority_tier=source.authority_tier,
                    trust_level=source.trust_level,
                    excerpt=doctrine.content[:300] if doctrine.content else None,
                    relevance_score=1.0,  # Would be computed by relevance algorithm
                    version_context=doctrine.version_metadata.version_introduced if doctrine.version_metadata else None
                ))

        return evidence

    def _find_controlling_evidence(self, evidence: List[EvidenceItem]) -> Optional[EvidenceItem]:
        """Find the highest authority evidence."""
        if not evidence:
            return None

        return max(evidence, key=lambda e: e.authority_tier.value)

    def _assess_evidence_quality(self, evidence: List[EvidenceItem]) -> str:
        """Assess overall evidence quality."""
        if not evidence:
            return "NONE"

        primary_count = sum(1 for e in evidence if e.authority_tier == AuthorityTier.PRIMARY_SOURCE)
        canonical_count = sum(1 for e in evidence if e.authority_tier == AuthorityTier.CANONICAL_ENGINEERING)

        if primary_count >= 2 or (primary_count >= 1 and canonical_count >= 1):
            return "STRONG"
        elif primary_count >= 1 or canonical_count >= 2:
            return "MODERATE"
        else:
            return "WEAK"

    def _determine_authority_tier(self, evidence: List[EvidenceItem]) -> AuthorityTier:
        """Determine overall authority tier from evidence."""
        if not evidence:
            return AuthorityTier.COMMUNITY_KNOWLEDGE

        return max(e.authority_tier for e in evidence)

    def _calculate_confidence(
        self,
        evidence: List[EvidenceItem],
        evidence_quality: str,
        doctrines: List[EngineeringDoctrine]
    ) -> tuple[ConfidenceTier, float, str]:
        """Calculate confidence tier and score."""
        if not evidence:
            return (
                ConfidenceTier.REQUIRES_REVIEW,
                0.2,
                "No evidence available - requires human review"
            )

        # Base confidence from evidence quality
        quality_scores = {"STRONG": 0.8, "MODERATE": 0.6, "WEAK": 0.4, "NONE": 0.2}
        base_score = quality_scores.get(evidence_quality, 0.3)

        # Adjust for evidence count
        if len(evidence) >= 3:
            base_score += 0.1
        elif len(evidence) == 1:
            base_score -= 0.1

        # Adjust for version metadata completeness
        has_version = any(d.version_metadata for d in doctrines)
        if has_version:
            base_score += 0.05
        else:
            base_score -= 0.1

        # Clamp score
        final_score = max(0.1, min(0.95, base_score))

        # Determine tier
        if final_score >= 0.9:
            tier = ConfidenceTier.DETERMINISTIC
            reasoning = "High-quality evidence from multiple authoritative sources"
        elif final_score >= 0.75:
            tier = ConfidenceTier.HIGH_CONFIDENCE
            reasoning = "Strong evidence with minor gaps"
        elif final_score >= 0.5:
            tier = ConfidenceTier.MODERATE
            reasoning = "Adequate evidence but some uncertainty"
        elif final_score >= 0.3:
            tier = ConfidenceTier.LOW_CONFIDENCE
            reasoning = "Limited evidence - use with caution"
        else:
            tier = ConfidenceTier.REQUIRES_REVIEW
            reasoning = "Insufficient evidence - requires human verification"

        return tier, final_score, reasoning

    def _identify_known_unknowns(
        self,
        doctrines: List[EngineeringDoctrine],
        context: Optional[Dict]
    ) -> List[KnownUnknown]:
        """Identify explicit gaps in knowledge."""
        unknowns = []

        # Check for missing version metadata
        without_version = [d for d in doctrines if not d.version_metadata]
        if without_version:
            unknowns.append(KnownUnknown(
                area="Version Information",
                description=f"{len(without_version)} source(s) lack version metadata",
                impact="Cannot verify version compatibility",
                resolution_path="Verify versions against current documentation"
            ))

        # Check for stale sources
        stale_sources = []
        for doctrine in doctrines:
            if doctrine.version_metadata and doctrine.version_metadata.last_verified:
                days = (datetime.now() - doctrine.version_metadata.last_verified).days
                if days > 90:
                    stale_sources.append(doctrine.doctrine_id)

        if stale_sources:
            unknowns.append(KnownUnknown(
                area="Source Freshness",
                description=f"{len(stale_sources)} source(s) not verified recently",
                impact="Information may be outdated",
                resolution_path="Re-verify against current official documentation"
            ))

        # Check for community-only sources
        community_only = all(
            d.authority_weight <= AuthorityTier.COMMUNITY_KNOWLEDGE.value
            for d in doctrines if d.source_references
        )
        if community_only and doctrines:
            unknowns.append(KnownUnknown(
                area="Authority",
                description="All sources are community-level (not official)",
                impact="Higher risk of inaccuracy",
                resolution_path="Verify against official vendor documentation"
            ))

        return unknowns

    def _identify_assumptions(
        self,
        doctrines: List[EngineeringDoctrine],
        claim: str
    ) -> List[str]:
        """Identify assumptions underlying the judgment."""
        assumptions = []

        # Version assumptions
        has_version = any(d.version_metadata for d in doctrines)
        if has_version:
            versions = [
                d.version_metadata.version_introduced
                for d in doctrines
                if d.version_metadata and d.version_metadata.version_introduced
            ]
            if versions:
                assumptions.append(f"Assumes version context: {', '.join(list(set(versions))[:3])}")

        # Platform assumptions
        assumptions.append("Assumes standard runtime environment")

        # Configuration assumptions
        assumptions.append("Assumes default configuration unless otherwise specified")

        return assumptions

    def _generate_caveats(
        self,
        doctrines: List[EngineeringDoctrine],
        evidence: List[EvidenceItem]
    ) -> List[str]:
        """Generate caveats for the judgment."""
        caveats = []

        # Deprecation caveats
        deprecated = [
            d for d in doctrines
            if d.version_metadata and d.version_metadata.status == VersionStatus.DEPRECATED
        ]
        if deprecated:
            caveats.append(f"{len(deprecated)} source(s) reference deprecated features")

        # Single-source caveat
        if len(evidence) == 1:
            caveats.append("Based on single source - consider additional verification")

        # Low authority caveat
        if all(e.authority_tier.value <= 40 for e in evidence):
            caveats.append("No primary or canonical sources - higher uncertainty")

        return caveats

    def _define_refusal_conditions(
        self,
        doctrines: List[EngineeringDoctrine]
    ) -> List[RefusalCondition]:
        """Define conditions when this judgment should not be trusted."""
        conditions = []

        conditions.append(RefusalCondition(
            condition="Target version differs significantly",
            reason=RefusalReason.MISSING_VERSION,
            applies_when="When using a version more than 2 major versions different",
            alternative_guidance="Re-query with specific version context"
        ))

        conditions.append(RefusalCondition(
            condition="Security-critical decision",
            reason=RefusalReason.SECURITY_CONCERN,
            applies_when="When making authentication/authorization decisions",
            alternative_guidance="Consult security team and official security advisories"
        ))

        conditions.append(RefusalCondition(
            condition="Production deployment",
            reason=RefusalReason.INSUFFICIENT_EVIDENCE,
            applies_when="Before deploying to production",
            alternative_guidance="Validate in staging environment first"
        ))

        return conditions

    def _check_version_context(
        self,
        doctrines: List[EngineeringDoctrine]
    ) -> tuple[Optional[str], List[str]]:
        """Check version context and generate warnings."""
        warnings = []
        versions = []

        for doctrine in doctrines:
            if doctrine.version_metadata:
                meta = doctrine.version_metadata
                if meta.version_introduced:
                    versions.append(meta.version_introduced)

                if meta.status == VersionStatus.DEPRECATED:
                    warnings.append(f"Deprecated: {doctrine.title}")
                elif meta.status == VersionStatus.REMOVED:
                    warnings.append(f"REMOVED: {doctrine.title}")

        version_context = ", ".join(set(versions[:3])) if versions else None

        return version_context, warnings

    def _build_reasoning(
        self,
        claim: str,
        evidence: List[EvidenceItem],
        controlling: Optional[EvidenceItem],
        doctrines: List[EngineeringDoctrine]
    ) -> str:
        """Build detailed reasoning chain."""
        parts = []

        parts.append(f"Claim: {claim}")
        parts.append("")

        if controlling:
            parts.append(f"Controlling Authority: {controlling.source_id}")
            parts.append(f"  - Authority Tier: {controlling.authority_tier.name}")
            parts.append(f"  - Trust Level: {controlling.trust_level.value}")
            parts.append("")

        if evidence:
            parts.append(f"Evidence Chain ({len(evidence)} source(s)):")
            for i, e in enumerate(evidence[:5], 1):
                parts.append(f"  {i}. {e.source_id} [{e.authority_tier.name}]")
            parts.append("")

        if doctrines:
            parts.append("Source Doctrines:")
            for d in doctrines[:3]:
                parts.append(f"  - {d.title}")
            parts.append("")

        parts.append("Reasoning: Based on the above evidence chain, the claim is supported by "
                    f"{len(evidence)} source(s) with controlling authority at "
                    f"{controlling.authority_tier.name if controlling else 'UNKNOWN'} tier.")

        return "\n".join(parts)

    def _build_summary(
        self,
        claim: str,
        confidence: ConfidenceTier,
        authority: AuthorityTier
    ) -> str:
        """Build brief summary."""
        return f"{claim} [Confidence: {confidence.value}, Authority: {authority.name}]"

    def format_for_output(
        self,
        judgment: EngineeringJudgment,
        format_type: str = "full"
    ) -> str:
        """Format judgment for different output types."""
        if format_type == "brief":
            return judgment.to_brief()
        elif format_type == "json":
            return json.dumps(judgment.to_dict(), indent=2)
        else:
            # Full format
            sections = []

            sections.append("=" * 60)
            sections.append(f"ENGINEERING JUDGMENT: {judgment.judgment_id}")
            sections.append("=" * 60)

            if judgment.is_refusal:
                sections.append(f"\n⚠️ REFUSAL: {judgment.refusal_reason.value}")
                sections.append(f"Explanation: {judgment.refusal_explanation}")
                sections.append("")

            sections.append(f"\n📋 CLAIM\n{judgment.claim}")

            sections.append(f"\n📊 CONFIDENCE")
            sections.append(f"  Tier: {judgment.confidence_tier.value}")
            sections.append(f"  Score: {judgment.confidence_score:.0%}")
            sections.append(f"  Reasoning: {judgment.confidence_reasoning}")

            sections.append(f"\n🏛️ AUTHORITY")
            sections.append(f"  Tier: {judgment.authority_tier.name}")
            sections.append(f"  Weight: {judgment.combined_authority_weight}")
            sections.append(f"  Trust: {judgment.trust_level.value}")
            sections.append(f"  Evidence Quality: {judgment.evidence_quality}")

            if judgment.evidence:
                sections.append(f"\n📚 EVIDENCE ({len(judgment.evidence)} sources)")
                for e in judgment.evidence[:5]:
                    sections.append(f"  - {e.source_id} [{e.authority_tier.name}]")

            if judgment.known_unknowns:
                sections.append(f"\n❓ KNOWN UNKNOWNS ({len(judgment.known_unknowns)})")
                for ku in judgment.known_unknowns:
                    sections.append(f"  - {ku.area}: {ku.description}")
                    sections.append(f"    Impact: {ku.impact}")

            if judgment.caveats:
                sections.append(f"\n⚠️ CAVEATS")
                for caveat in judgment.caveats:
                    sections.append(f"  - {caveat}")

            if judgment.refusal_conditions:
                sections.append(f"\n🚫 DO NOT USE WHEN:")
                for rc in judgment.refusal_conditions[:3]:
                    sections.append(f"  - {rc.condition}")
                    sections.append(f"    Reason: {rc.reason.value}")

            if judgment.version_warnings:
                sections.append(f"\n📅 VERSION WARNINGS")
                for warning in judgment.version_warnings:
                    sections.append(f"  - {warning}")

            sections.append(f"\n🔐 DETERMINISM HASH: {judgment.determinism_hash}")
            sections.append("=" * 60)

            return "\n".join(sections)


# Self-test
def _self_test():
    """Validate engineering judgment formatter."""
    from ..engine.models import SourceReference, AuthorityTier, TrustLevel, VersionMetadata

    formatter = EngineeringJudgmentFormatter()

    # Create test doctrine
    doctrine = EngineeringDoctrine(
        doctrine_id="test_doc",
        title="Test Doctrine",
        content="This is a test doctrine about API usage.",
        category="API",
        source_references=[
            SourceReference(
                source_id="google_docs",
                source_type="VENDOR_DOCS",
                authority_tier=AuthorityTier.PRIMARY_SOURCE,
                trust_level=TrustLevel.ABSOLUTE,
                vendor="google"
            )
        ],
        version_metadata=VersionMetadata(
            version_introduced="1.0.0",
            status=VersionStatus.ACTIVE
        ),
        authority_weight=100
    )

    # Create judgment
    judgment = formatter.create_judgment(
        claim="The API should be called with authentication headers",
        judgment_type=JudgmentType.RECOMMENDATION,
        doctrines=[doctrine]
    )

    assert judgment is not None, "Should create judgment"
    assert judgment.claim != "", "Should have claim"
    assert len(judgment.evidence) > 0, "Should have evidence"
    assert judgment.confidence_score > 0, "Should have confidence"
    assert judgment.determinism_hash is not None, "Should have hash"

    # Test refusal
    refusal = formatter.create_refusal(
        reason=RefusalReason.MISSING_VERSION,
        explanation="Cannot determine compatibility without version information",
        original_query="Is this API compatible?",
        what_would_help=["Specify target version", "Provide SDK version"]
    )

    assert refusal.is_refusal is True, "Should be refusal"
    assert refusal.refusal_reason == RefusalReason.MISSING_VERSION

    # Test output formatting
    brief = formatter.format_for_output(judgment, "brief")
    assert "CLAIM:" in brief, "Brief should have claim"

    full = formatter.format_for_output(judgment, "full")
    assert "ENGINEERING JUDGMENT" in full, "Full should have header"

    logger.info("Engineering Judgment Formatter self-test PASSED")


if __name__ == "__main__":
    _self_test()
