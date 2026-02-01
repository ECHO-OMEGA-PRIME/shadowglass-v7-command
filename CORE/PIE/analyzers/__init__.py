"""
PROGRAMMING INTELLIGENCE ENGINE - Analyzers Module

Enhanced analysis subsystems for deterministic engineering reasoning.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from .authority_classifier import (
    AuthorityClassificationEngine,
    ClassificationResult,
)

from .version_lifecycle import (
    VersionLifecycleEngine,
    ParsedVersion,
    VersionConstraint,
    LifecycleState,
    LifecyclePhase,
    VersionScheme,
    VersionCheckResult,
)

from .dependency_graph import (
    DependencyGraphAnalyzer,
    DependencyGraphReport,
    SPOFAnalysis,
    CascadeRisk,
    CircularDependency,
    HiddenOrchestrator,
    FragmentationAnalysis,
    RiskLevel,
)

from .drift_sentinel import (
    DriftSentinelReadOnly,
    DriftObservation,
    DriftSeverity,
    ContentSnapshot,
)

from .failure_mode import (
    FailureModeAnalyzer,
    FailureMode,
    FailureCategory,
    ImpactLevel,
    BehaviorDiscrepancy,
    FailureEvidence,
    PostmortemAnalysis,
)

__all__ = [
    # Authority Classification
    "AuthorityClassificationEngine",
    "ClassificationResult",

    # Version Lifecycle
    "VersionLifecycleEngine",
    "ParsedVersion",
    "VersionConstraint",
    "LifecycleState",
    "LifecyclePhase",
    "VersionScheme",
    "VersionCheckResult",

    # Dependency Graph
    "DependencyGraphAnalyzer",
    "DependencyGraphReport",
    "SPOFAnalysis",
    "CascadeRisk",
    "CircularDependency",
    "HiddenOrchestrator",
    "FragmentationAnalysis",
    "RiskLevel",

    # Drift Sentinel (Read-Only)
    "DriftSentinelReadOnly",
    "DriftObservation",
    "DriftSeverity",
    "ContentSnapshot",

    # Failure Mode
    "FailureModeAnalyzer",
    "FailureMode",
    "FailureCategory",
    "ImpactLevel",
    "BehaviorDiscrepancy",
    "FailureEvidence",
    "PostmortemAnalysis",
]
