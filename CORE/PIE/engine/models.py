"""
PROGRAMMING INTELLIGENCE ENGINE - Core Data Models
System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO

All data structures for the PIE cognitive architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
import hashlib
import json


class AuthorityTier(IntEnum):
    """Authority hierarchy weights - higher wins in conflicts."""
    PRIMARY_SOURCE = 100      # Official vendor docs
    CANONICAL_ENGINEERING = 80  # Kubernetes, Docker, Terraform
    STRUCTURED_TECHNICAL = 60   # RFCs, Standards, Security advisories
    VERIFIED_EXPERT = 40        # Maintainer blogs, deep dives
    COMMUNITY_KNOWLEDGE = 20    # StackOverflow, GitHub discussions


class TrustLevel(str, Enum):
    """Trust classification for source verification."""
    ABSOLUTE = "ABSOLUTE"      # Never question
    HIGH = "HIGH"              # Strong confidence
    FORMAL = "FORMAL"          # Standards-based
    VERIFIED = "VERIFIED"      # Expert-verified
    COMMUNITY = "COMMUNITY"    # Requires additional validation


class VersionStatus(str, Enum):
    """Lifecycle status of a versioned feature/API."""
    ACTIVE = "ACTIVE"                    # Current and supported
    DEPRECATED = "DEPRECATED"            # Still works, removal planned
    REMOVED = "REMOVED"                  # No longer available
    ALPHA = "ALPHA"                      # Experimental
    BETA = "BETA"                        # Pre-release
    LEGACY = "LEGACY"                    # Old but maintained
    END_OF_LIFE = "END_OF_LIFE"          # No longer maintained


class ConfidenceTier(str, Enum):
    """Confidence level for engineering decisions."""
    DETERMINISTIC = "DETERMINISTIC"      # Absolute certainty
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"  # Strong evidence
    MODERATE = "MODERATE"                # Reasonable confidence
    LOW_CONFIDENCE = "LOW_CONFIDENCE"    # Uncertain
    REQUIRES_REVIEW = "REQUIRES_REVIEW"  # Human verification needed


class DriftType(str, Enum):
    """Types of documentation drift detected."""
    DEPRECATION = "DEPRECATION"
    VERSION_SUNSET = "VERSION_SUNSET"
    SECURITY_ADVISORY = "SECURITY_ADVISORY"
    BREAKING_CHANGE = "BREAKING_CHANGE"
    API_REMOVAL = "API_REMOVAL"
    BEHAVIOR_CHANGE = "BEHAVIOR_CHANGE"


@dataclass
class VersionMetadata:
    """
    LAYER 2: Version Awareness - Critical metadata for every doctrine.
    This prevents the #1 failure mode of AI coding tools.
    """
    version_introduced: Optional[str] = None
    version_deprecated: Optional[str] = None
    version_removed: Optional[str] = None
    replacement_path: Optional[str] = None
    breaking_changes: List[str] = field(default_factory=list)
    compatibility_notes: List[str] = field(default_factory=list)
    status: VersionStatus = VersionStatus.ACTIVE
    last_verified: Optional[datetime] = None

    def is_safe_for_version(self, target_version: str) -> tuple[bool, str]:
        """Check if this doctrine is safe for a specific version."""
        if self.version_removed and self._compare_versions(target_version, self.version_removed) >= 0:
            return False, f"Removed in {self.version_removed}. Use: {self.replacement_path or 'No replacement specified'}"
        if self.version_deprecated and self._compare_versions(target_version, self.version_deprecated) >= 0:
            return True, f"Deprecated since {self.version_deprecated}. Consider: {self.replacement_path}"
        if self.version_introduced and self._compare_versions(target_version, self.version_introduced) < 0:
            return False, f"Not available until {self.version_introduced}"
        return True, "Compatible"

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare semantic versions. Returns -1, 0, or 1."""
        try:
            parts1 = [int(x) for x in v1.lstrip('v').split('.')[:3]]
            parts2 = [int(x) for x in v2.lstrip('v').split('.')[:3]]
            while len(parts1) < 3:
                parts1.append(0)
            while len(parts2) < 3:
                parts2.append(0)
            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                if p1 > p2:
                    return 1
            return 0
        except (ValueError, AttributeError):
            return 0  # Unable to compare, assume compatible


@dataclass
class SourceReference:
    """Reference to the authoritative source of doctrine."""
    source_id: str
    source_type: str
    authority_tier: AuthorityTier
    trust_level: TrustLevel
    url: Optional[str] = None
    file_path: Optional[Path] = None
    last_accessed: Optional[datetime] = None
    content_hash: Optional[str] = None
    vendor: Optional[str] = None

    def compute_content_hash(self, content: str) -> str:
        """Compute deterministic hash for content verification."""
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()
        return self.content_hash


@dataclass
class GraphNode:
    """
    LAYER 3: Semantic Engineering Graph node.
    Represents an entity in the dependency graph.
    """
    node_id: str
    node_type: str  # API, SDK, Language, Runtime, Infrastructure, Auth, etc.
    name: str
    version: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # node_ids
    dependents: List[str] = field(default_factory=list)    # node_ids that depend on this
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_dependency(self, node_id: str):
        if node_id not in self.dependencies:
            self.dependencies.append(node_id)

    def add_dependent(self, node_id: str):
        if node_id not in self.dependents:
            self.dependents.append(node_id)


@dataclass
class EngineeringDoctrine:
    """
    LAYER 4: Deterministic Engineering Doctrine.
    The atomic unit of institutional knowledge.

    Identical query → identical conclusion.
    No stochastic drift.
    """
    doctrine_id: str
    title: str
    content: str
    category: str  # API, Pattern, Security, Architecture, etc.

    # Authority chain
    source_references: List[SourceReference] = field(default_factory=list)
    authority_weight: int = 0  # Computed from highest authority source

    # Version awareness (Layer 2)
    version_metadata: Optional[VersionMetadata] = None

    # Graph connections (Layer 3)
    related_nodes: List[str] = field(default_factory=list)  # GraphNode IDs

    # Determinism guarantees (Layer 4)
    determinism_hash: Optional[str] = None
    confidence_tier: ConfidenceTier = ConfidenceTier.MODERATE

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

    def compute_determinism_hash(self) -> str:
        """
        Compute deterministic hash for identical reasoning verification.
        Same inputs must produce same outputs.
        """
        hash_input = json.dumps({
            "doctrine_id": self.doctrine_id,
            "content": self.content,
            "authority_weight": self.authority_weight,
            "sources": [s.content_hash for s in self.source_references if s.content_hash],
            "version_status": self.version_metadata.status.value if self.version_metadata else None
        }, sort_keys=True)
        self.determinism_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        return self.determinism_hash

    def get_controlling_source(self) -> Optional[SourceReference]:
        """Return the highest-authority source (controlling authority)."""
        if not self.source_references:
            return None
        return max(self.source_references, key=lambda s: s.authority_tier.value)

    def to_decision_report(self) -> Dict[str, Any]:
        """Generate a defensible engineering decision report."""
        controlling = self.get_controlling_source()
        return {
            "doctrine_id": self.doctrine_id,
            "title": self.title,
            "determinism_hash": self.determinism_hash,
            "authority_weight": self.authority_weight,
            "confidence_tier": self.confidence_tier.value,
            "controlling_source": {
                "source_id": controlling.source_id if controlling else None,
                "authority_tier": controlling.authority_tier.value if controlling else None,
                "trust_level": controlling.trust_level.value if controlling else None
            },
            "version_status": self.version_metadata.status.value if self.version_metadata else "UNKNOWN",
            "defensibility": "HIGH" if self.authority_weight >= 60 else "MODERATE" if self.authority_weight >= 40 else "REQUIRES_REVIEW"
        }


@dataclass
class DriftAlert:
    """Alert generated by Documentation Drift Sentinel."""
    alert_id: str
    drift_type: DriftType
    affected_doctrines: List[str]  # doctrine_ids
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    detected_at: datetime = field(default_factory=datetime.now)
    source_trigger: Optional[str] = None
    description: str = ""
    migration_path: Optional[str] = None
    auto_remediated: bool = False
    remediation_notes: Optional[str] = None


@dataclass
class QueryResult:
    """Result from a PIE engineering query."""
    query_id: str
    query_text: str
    doctrines: List[EngineeringDoctrine]
    reasoning_chain: List[str]  # Step-by-step reasoning
    final_recommendation: str
    confidence: ConfidenceTier
    authority_report: Dict[str, Any]
    version_warnings: List[str]
    conflicts_resolved: List[Dict[str, Any]]
    determinism_hash: str  # Hash of the entire reasoning process
    processed_at: datetime = field(default_factory=datetime.now)

    def compute_result_hash(self) -> str:
        """Ensure identical queries produce identical results."""
        hash_input = json.dumps({
            "query": self.query_text,
            "doctrines": [d.doctrine_id for d in self.doctrines],
            "recommendation": self.final_recommendation,
            "confidence": self.confidence.value
        }, sort_keys=True)
        self.determinism_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        return self.determinism_hash


@dataclass
class IngestionRecord:
    """Record of document ingestion for audit trail."""
    record_id: str
    source_path: str
    source_type: str
    authority_tier: AuthorityTier
    ingested_at: datetime = field(default_factory=datetime.now)
    doctrines_created: int = 0
    graph_nodes_created: int = 0
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    content_hash: Optional[str] = None
