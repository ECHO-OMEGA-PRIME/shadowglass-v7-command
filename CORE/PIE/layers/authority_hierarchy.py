"""
PROGRAMMING INTELLIGENCE ENGINE - LAYER 1
Authority Hierarchy Engine

Every document is ranked by institutional authority.
When sources conflict: HIGHER AUTHORITY WINS AUTOMATICALLY.
No ambiguity tolerated.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json
import re
from loguru import logger

from ..engine.models import (
    AuthorityTier,
    TrustLevel,
    SourceReference,
    EngineeringDoctrine,
    ConfidenceTier
)


@dataclass
class AuthorityClassification:
    """Result of classifying a source's authority."""
    tier: AuthorityTier
    trust_level: TrustLevel
    vendor: Optional[str]
    source_type: str
    confidence: float
    reasoning: str


class AuthorityHierarchyEngine:
    """
    LAYER 1: Authority Hierarchy Engine

    Ranks every document by institutional authority.
    Higher authority wins in all conflicts.
    No ambiguity tolerated.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent / "config" / "authority_tiers.json"
        self.authority_config = self._load_config()
        self.vendor_patterns = self._build_vendor_patterns()
        self.classification_cache: Dict[str, AuthorityClassification] = {}

        logger.info("Authority Hierarchy Engine initialized")

    def _load_config(self) -> Dict:
        """Load authority tier configuration."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Default authority configuration."""
        return {
            "AUTHORITY_HIERARCHY": {
                "TIER_100": {"weight": 100, "name": "Primary Sources"},
                "TIER_80": {"weight": 80, "name": "Canonical Engineering"},
                "TIER_60": {"weight": 60, "name": "Structured Technical"},
                "TIER_40": {"weight": 40, "name": "Verified Expert"},
                "TIER_20": {"weight": 20, "name": "Community Knowledge"}
            }
        }

    def _build_vendor_patterns(self) -> Dict[str, Dict]:
        """Build regex patterns for vendor detection."""
        return {
            # TIER 100 - Primary Sources
            "apple": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"developer\.apple\.com",
                    r"apple\.com/documentation",
                    r"swift\.org",
                    r"xcode",
                    r"ios\s*sdk",
                    r"swiftui"
                ]
            },
            "google": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"cloud\.google\.com/docs",
                    r"developers\.google\.com",
                    r"firebase\.google\.com",
                    r"android\.com",
                    r"developer\.android\.com",
                    r"golang\.org",
                    r"go\.dev"
                ]
            },
            "microsoft": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"docs\.microsoft\.com",
                    r"learn\.microsoft\.com",
                    r"azure\.microsoft\.com",
                    r"typescript\s*(official|handbook)",
                    r"dotnet",
                    r"\.net\s*documentation"
                ]
            },
            "aws": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"docs\.aws\.amazon\.com",
                    r"aws\.amazon\.com/documentation",
                    r"awsdocs"
                ]
            },
            "python": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"docs\.python\.org",
                    r"python\.org/dev/peps",
                    r"peps\.python\.org"
                ]
            },
            "rust": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"doc\.rust-lang\.org",
                    r"rust-lang\.org",
                    r"crates\.io"
                ]
            },
            "react": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"react\.dev",
                    r"reactjs\.org",
                    r"legacy\.reactjs\.org"
                ]
            },
            "nextjs": {
                "tier": AuthorityTier.PRIMARY_SOURCE,
                "trust": TrustLevel.ABSOLUTE,
                "patterns": [
                    r"nextjs\.org/docs",
                    r"vercel\.com/docs"
                ]
            },

            # TIER 80 - Canonical Engineering
            "kubernetes": {
                "tier": AuthorityTier.CANONICAL_ENGINEERING,
                "trust": TrustLevel.HIGH,
                "patterns": [
                    r"kubernetes\.io/docs",
                    r"k8s\.io"
                ]
            },
            "docker": {
                "tier": AuthorityTier.CANONICAL_ENGINEERING,
                "trust": TrustLevel.HIGH,
                "patterns": [
                    r"docs\.docker\.com",
                    r"docker\.com/docs"
                ]
            },
            "terraform": {
                "tier": AuthorityTier.CANONICAL_ENGINEERING,
                "trust": TrustLevel.HIGH,
                "patterns": [
                    r"terraform\.io/docs",
                    r"registry\.terraform\.io"
                ]
            },
            "github": {
                "tier": AuthorityTier.CANONICAL_ENGINEERING,
                "trust": TrustLevel.HIGH,
                "patterns": [
                    r"docs\.github\.com",
                    r"github\.com/docs"
                ]
            },

            # TIER 60 - Structured Technical
            "rfc": {
                "tier": AuthorityTier.STRUCTURED_TECHNICAL,
                "trust": TrustLevel.FORMAL,
                "patterns": [
                    r"rfc\s*\d+",
                    r"ietf\.org",
                    r"datatracker\.ietf\.org"
                ]
            },
            "w3c": {
                "tier": AuthorityTier.STRUCTURED_TECHNICAL,
                "trust": TrustLevel.FORMAL,
                "patterns": [
                    r"w3\.org",
                    r"w3c\s*specification"
                ]
            },
            "owasp": {
                "tier": AuthorityTier.STRUCTURED_TECHNICAL,
                "trust": TrustLevel.FORMAL,
                "patterns": [
                    r"owasp\.org",
                    r"owasp\s*top\s*10"
                ]
            },

            # TIER 20 - Community Knowledge
            "stackoverflow": {
                "tier": AuthorityTier.COMMUNITY_KNOWLEDGE,
                "trust": TrustLevel.COMMUNITY,
                "patterns": [
                    r"stackoverflow\.com",
                    r"stack\s*overflow"
                ]
            },
            "github_discussions": {
                "tier": AuthorityTier.COMMUNITY_KNOWLEDGE,
                "trust": TrustLevel.COMMUNITY,
                "patterns": [
                    r"github\.com/.*/discussions",
                    r"github\.com/.*/issues"
                ]
            }
        }

    def classify_source(
        self,
        source_path: Optional[str] = None,
        source_url: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> AuthorityClassification:
        """
        Classify a source's authority tier.

        Args:
            source_path: File path of the source
            source_url: URL of the source
            content: Content to analyze for classification hints
            metadata: Additional metadata (vendor, type, etc.)

        Returns:
            AuthorityClassification with tier and reasoning
        """
        cache_key = f"{source_path}:{source_url}"
        if cache_key in self.classification_cache:
            return self.classification_cache[cache_key]

        # Check URL patterns first (most reliable)
        if source_url:
            classification = self._classify_by_url(source_url)
            if classification:
                self.classification_cache[cache_key] = classification
                return classification

        # Check file path patterns
        if source_path:
            classification = self._classify_by_path(source_path)
            if classification:
                self.classification_cache[cache_key] = classification
                return classification

        # Check metadata
        if metadata and "vendor" in metadata:
            classification = self._classify_by_vendor(metadata["vendor"])
            if classification:
                self.classification_cache[cache_key] = classification
                return classification

        # Content analysis (fallback)
        if content:
            classification = self._classify_by_content(content)
            if classification:
                self.classification_cache[cache_key] = classification
                return classification

        # Default: Community Knowledge (lowest tier)
        default = AuthorityClassification(
            tier=AuthorityTier.COMMUNITY_KNOWLEDGE,
            trust_level=TrustLevel.COMMUNITY,
            vendor=None,
            source_type="unknown",
            confidence=0.3,
            reasoning="Unable to classify source. Assigned lowest tier for safety."
        )
        self.classification_cache[cache_key] = default
        return default

    def _classify_by_url(self, url: str) -> Optional[AuthorityClassification]:
        """Classify based on URL patterns."""
        url_lower = url.lower()
        for vendor, config in self.vendor_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    return AuthorityClassification(
                        tier=config["tier"],
                        trust_level=config["trust"],
                        vendor=vendor,
                        source_type="official_documentation",
                        confidence=0.95,
                        reasoning=f"URL pattern matched: {pattern} → {vendor} (Tier {config['tier'].value})"
                    )
        return None

    def _classify_by_path(self, path: str) -> Optional[AuthorityClassification]:
        """Classify based on file path patterns."""
        path_lower = path.lower()

        # Check for known vendor directories
        vendor_dirs = {
            "apple": (AuthorityTier.PRIMARY_SOURCE, TrustLevel.ABSOLUTE),
            "google": (AuthorityTier.PRIMARY_SOURCE, TrustLevel.ABSOLUTE),
            "microsoft": (AuthorityTier.PRIMARY_SOURCE, TrustLevel.ABSOLUTE),
            "aws": (AuthorityTier.PRIMARY_SOURCE, TrustLevel.ABSOLUTE),
            "python": (AuthorityTier.PRIMARY_SOURCE, TrustLevel.ABSOLUTE),
            "kubernetes": (AuthorityTier.CANONICAL_ENGINEERING, TrustLevel.HIGH),
            "docker": (AuthorityTier.CANONICAL_ENGINEERING, TrustLevel.HIGH),
            "terraform": (AuthorityTier.CANONICAL_ENGINEERING, TrustLevel.HIGH),
        }

        for vendor, (tier, trust) in vendor_dirs.items():
            if vendor in path_lower:
                return AuthorityClassification(
                    tier=tier,
                    trust_level=trust,
                    vendor=vendor,
                    source_type="local_documentation",
                    confidence=0.8,
                    reasoning=f"Path contains vendor indicator: {vendor}"
                )
        return None

    def _classify_by_vendor(self, vendor: str) -> Optional[AuthorityClassification]:
        """Classify based on explicit vendor metadata."""
        vendor_lower = vendor.lower()
        if vendor_lower in self.vendor_patterns:
            config = self.vendor_patterns[vendor_lower]
            return AuthorityClassification(
                tier=config["tier"],
                trust_level=config["trust"],
                vendor=vendor_lower,
                source_type="metadata_classified",
                confidence=0.9,
                reasoning=f"Vendor explicitly specified: {vendor}"
            )
        return None

    def _classify_by_content(self, content: str) -> Optional[AuthorityClassification]:
        """Classify based on content analysis (least reliable)."""
        content_lower = content.lower()[:5000]  # First 5000 chars

        for vendor, config in self.vendor_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    return AuthorityClassification(
                        tier=config["tier"],
                        trust_level=config["trust"],
                        vendor=vendor,
                        source_type="content_inferred",
                        confidence=0.6,
                        reasoning=f"Content pattern matched: {pattern} (lower confidence)"
                    )
        return None

    def resolve_conflict(
        self,
        doctrines: List[EngineeringDoctrine]
    ) -> Tuple[EngineeringDoctrine, Dict[str, Any]]:
        """
        Resolve conflict between multiple doctrines.
        RULE: Higher authority ALWAYS wins.

        Args:
            doctrines: List of potentially conflicting doctrines

        Returns:
            Winning doctrine and conflict resolution report
        """
        if not doctrines:
            raise ValueError("No doctrines provided for conflict resolution")

        if len(doctrines) == 1:
            return doctrines[0], {"conflict": False, "resolution": "Single source"}

        # Sort by authority weight (descending)
        sorted_doctrines = sorted(
            doctrines,
            key=lambda d: d.authority_weight,
            reverse=True
        )

        winner = sorted_doctrines[0]
        losers = sorted_doctrines[1:]

        # Check for tie at top
        if len(sorted_doctrines) > 1 and sorted_doctrines[0].authority_weight == sorted_doctrines[1].authority_weight:
            # Tie-breaker: most recent version
            winner = self._resolve_tie(sorted_doctrines[0], sorted_doctrines[1])

        resolution_report = {
            "conflict": True,
            "resolution": "HIGHER_AUTHORITY_WINS",
            "winner": {
                "doctrine_id": winner.doctrine_id,
                "authority_weight": winner.authority_weight,
                "controlling_source": winner.get_controlling_source().source_id if winner.get_controlling_source() else None
            },
            "defeated": [
                {
                    "doctrine_id": d.doctrine_id,
                    "authority_weight": d.authority_weight,
                    "reason": f"Lower authority ({d.authority_weight} < {winner.authority_weight})"
                }
                for d in losers
            ],
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Conflict resolved: {winner.doctrine_id} wins with authority {winner.authority_weight}")
        return winner, resolution_report

    def _resolve_tie(
        self,
        doctrine1: EngineeringDoctrine,
        doctrine2: EngineeringDoctrine
    ) -> EngineeringDoctrine:
        """Resolve tie using secondary criteria."""
        # Tie-breaker 1: More recent version
        if doctrine1.version_metadata and doctrine2.version_metadata:
            if doctrine1.version_metadata.last_verified and doctrine2.version_metadata.last_verified:
                if doctrine1.version_metadata.last_verified > doctrine2.version_metadata.last_verified:
                    return doctrine1
                return doctrine2

        # Tie-breaker 2: Higher confidence tier
        confidence_order = [
            ConfidenceTier.DETERMINISTIC,
            ConfidenceTier.HIGH_CONFIDENCE,
            ConfidenceTier.MODERATE,
            ConfidenceTier.LOW_CONFIDENCE,
            ConfidenceTier.REQUIRES_REVIEW
        ]
        if confidence_order.index(doctrine1.confidence_tier) < confidence_order.index(doctrine2.confidence_tier):
            return doctrine1
        return doctrine2

    def compute_authority_weight(self, doctrine: EngineeringDoctrine) -> int:
        """
        Compute the overall authority weight for a doctrine.
        Uses the highest-authority source.
        """
        if not doctrine.source_references:
            return 0

        max_weight = max(
            source.authority_tier.value
            for source in doctrine.source_references
        )
        doctrine.authority_weight = max_weight
        return max_weight

    def create_source_reference(
        self,
        source_id: str,
        classification: AuthorityClassification,
        url: Optional[str] = None,
        file_path: Optional[Path] = None,
        content: Optional[str] = None
    ) -> SourceReference:
        """Create a properly classified source reference."""
        ref = SourceReference(
            source_id=source_id,
            source_type=classification.source_type,
            authority_tier=classification.tier,
            trust_level=classification.trust_level,
            url=url,
            file_path=file_path,
            last_accessed=datetime.now(),
            vendor=classification.vendor
        )
        if content:
            ref.compute_content_hash(content)
        return ref
