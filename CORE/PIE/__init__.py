"""
PROGRAMMING INTELLIGENCE ENGINE (PIE)

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
Authority: Commander Bobby Don McWilliams II

A deterministic cognitive architecture for engineering decisions.
Not a vector search bot - a judgment engine.

Four-Layer Cognitive Stack:
1. Authority Hierarchy Engine - Source ranking and conflict resolution
2. Version Awareness Engine - Lifecycle tracking, never hallucinate compatibility
3. Semantic Engineering Graph - Dependency reasoning, not document blobs
4. Deterministic Doctrine Engine - Identical query → identical conclusion

Enhanced Subsystems (v2.0):
- Authority Classification Engine - Source TYPE categorization
- Version & Lifecycle Engine - Explicit version parsing with refusal
- Dependency Graph Analyzer - SPOF and cascade risk detection
- Drift Sentinel (Read-Only) - Observer-only drift detection
- Failure Mode Analyzer - Postmortem and CVE analysis
- Engineering Judgment Formatter - Structured output with refusal conditions
- Authority Registry - Immutable source classifications

REASONING_ISOLATION_PROTOCOL:
No OMNISCIENT memory calls during cognition.
Observation only. Never interference.
"""

from .engine.models import (
    AuthorityTier,
    TrustLevel,
    VersionStatus,
    ConfidenceTier,
    DriftType,
    VersionMetadata,
    SourceReference,
    GraphNode,
    EngineeringDoctrine,
    DriftAlert,
    QueryResult,
    IngestionRecord
)

from .layers.authority_hierarchy import AuthorityHierarchyEngine
from .layers.version_awareness import VersionAwarenessEngine
from .layers.semantic_graph import SemanticEngineeringGraph
from .layers.deterministic_doctrine import DeterministicDoctrineEngine, DoctrineQuery

from .sentinel.drift_sentinel import DriftSentinel
from .ingestion.pipeline import IngestionPipeline, IngestionConfig

# Enhanced Analyzers (v2.0)
from .analyzers import (
    AuthorityClassificationEngine,
    ClassificationResult,
    VersionLifecycleEngine,
    ParsedVersion,
    VersionConstraint,
    LifecycleState,
    LifecyclePhase,
    VersionCheckResult,
    DependencyGraphAnalyzer,
    DependencyGraphReport,
    SPOFAnalysis,
    CascadeRisk,
    CircularDependency,
    HiddenOrchestrator,
    FragmentationAnalysis,
    DriftSentinelReadOnly,
    DriftObservation,
    DriftSeverity,
    FailureModeAnalyzer,
    FailureMode,
    FailureCategory,
    ImpactLevel,
    BehaviorDiscrepancy,
    PostmortemAnalysis,
)

# Judgment Formatting (v2.0)
from .judgment import (
    EngineeringJudgmentFormatter,
    EngineeringJudgment,
    JudgmentType,
    RefusalReason,
    EvidenceItem,
    KnownUnknown,
    RefusalCondition,
)

# Authority Registry (v2.0)
from .registry import (
    AuthorityRegistry,
    AuthorityRecord,
    SourceType,
    SourceTypeWeight,
)

__version__ = "2.0.0"
__author__ = "ECHO OMEGA PRIME"
__governance_tier__ = "ZERO"
__classification__ = "ISOLATED_REASONING_ENGINE"

__all__ = [
    # Core Models
    "AuthorityTier",
    "TrustLevel",
    "VersionStatus",
    "ConfidenceTier",
    "DriftType",
    "VersionMetadata",
    "SourceReference",
    "GraphNode",
    "EngineeringDoctrine",
    "DriftAlert",
    "QueryResult",
    "IngestionRecord",

    # Original Layers
    "AuthorityHierarchyEngine",
    "VersionAwarenessEngine",
    "SemanticEngineeringGraph",
    "DeterministicDoctrineEngine",
    "DoctrineQuery",

    # Original Sentinel
    "DriftSentinel",

    # Ingestion
    "IngestionPipeline",
    "IngestionConfig",

    # Enhanced Analyzers (v2.0)
    "AuthorityClassificationEngine",
    "ClassificationResult",
    "VersionLifecycleEngine",
    "ParsedVersion",
    "VersionConstraint",
    "LifecycleState",
    "LifecyclePhase",
    "VersionCheckResult",
    "DependencyGraphAnalyzer",
    "DependencyGraphReport",
    "SPOFAnalysis",
    "CascadeRisk",
    "CircularDependency",
    "HiddenOrchestrator",
    "FragmentationAnalysis",
    "DriftSentinelReadOnly",
    "DriftObservation",
    "DriftSeverity",
    "FailureModeAnalyzer",
    "FailureMode",
    "FailureCategory",
    "ImpactLevel",
    "BehaviorDiscrepancy",
    "PostmortemAnalysis",

    # Judgment Formatting (v2.0)
    "EngineeringJudgmentFormatter",
    "EngineeringJudgment",
    "JudgmentType",
    "RefusalReason",
    "EvidenceItem",
    "KnownUnknown",
    "RefusalCondition",

    # Authority Registry (v2.0)
    "AuthorityRegistry",
    "AuthorityRecord",
    "SourceType",
    "SourceTypeWeight",
]
