"""
PROGRAMMING INTELLIGENCE ENGINE - STRATEGIC ANALYZER
ENGINEERING OBSERVER STATE

Role: ARCHITECTURAL PATTERN INTELLIGENCE
Function: INTERPRETATION — NOT MUTATION

You are the systems physicist, not the construction crew.

Mission: Analyze cartography artifacts and surface:
- Dependency risks
- Version conflicts
- Hidden orchestrators
- Architectural contradictions
- Deprecation exposure
- Authority collisions
- Fragmentation vectors

HARD PROHIBITIONS:
- No write operations
- No structural changes
- No ingestion
- No drift corrections
- No auto-refactors

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
State: ENGINEERING_OBSERVER
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
import hashlib
from loguru import logger

from ..engine.models import (
    EngineeringDoctrine,
    VersionStatus,
    ConfidenceTier,
    AuthorityTier
)
from ..layers.semantic_graph import SemanticEngineeringGraph


class AnalysisType:
    """Types of strategic analysis."""
    DEPENDENCY_RISK = "DEPENDENCY_RISK"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    HIDDEN_ORCHESTRATOR = "HIDDEN_ORCHESTRATOR"
    ARCHITECTURAL_CONTRADICTION = "ARCHITECTURAL_CONTRADICTION"
    DEPRECATION_EXPOSURE = "DEPRECATION_EXPOSURE"
    AUTHORITY_COLLISION = "AUTHORITY_COLLISION"
    FRAGMENTATION_VECTOR = "FRAGMENTATION_VECTOR"


@dataclass
class RiskFinding:
    """A risk or issue discovered during analysis."""
    finding_id: str
    analysis_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: str
    description: str
    affected_components: List[str]
    evidence: List[str]
    recommendation: str
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class ArchitecturalBriefing:
    """Complete architectural analysis briefing."""
    briefing_id: str
    generated_at: datetime
    scope: str
    findings: List[RiskFinding]
    summary: Dict[str, Any]
    risk_score: float
    recommendations: List[str]


class StrategicAnalyzer:
    """
    ARCHITECTURAL PATTERN INTELLIGENCE

    Observes. Interprets. Does NOT mutate.

    The clarity of cartography depends on environmental stability.
    """

    def __init__(
        self,
        graph: SemanticEngineeringGraph,
        doctrines: Dict[str, EngineeringDoctrine]
    ):
        self.graph = graph
        self.doctrines = doctrines

        # Verify observer state
        self._verify_observer_state()

        # Analysis cache (read-only)
        self._analysis_cache: Dict[str, ArchitecturalBriefing] = {}

        logger.info("Strategic Analyzer initialized in OBSERVER STATE")
        logger.info("MUTATION_ENGINE: OFF | AUTONOMOUS_REFACTOR: DISABLED")

    def _verify_observer_state(self):
        """Verify observer state is active before proceeding."""
        config_path = Path(__file__).parent.parent / "config" / "observer_state.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                if not config.get("FLAGS", {}).get("ENGINEERING_OBSERVER", False):
                    raise RuntimeError("Observer state not active")
                if config.get("FLAGS", {}).get("MUTATION_ENGINE", True):
                    raise RuntimeError("Mutation engine must be disabled")
        logger.info("Observer state verified: ACTIVE")

    # =========================================================================
    # DEPENDENCY RISK ANALYSIS
    # =========================================================================

    def analyze_dependency_risks(self) -> List[RiskFinding]:
        """
        Analyze dependency graph for risks.
        READ-ONLY operation.
        """
        findings = []

        # Find circular dependencies
        cycles = self._detect_cycles()
        for cycle in cycles:
            findings.append(RiskFinding(
                finding_id=f"dep_cycle_{hashlib.sha256(''.join(cycle).encode()).hexdigest()[:8]}",
                analysis_type=AnalysisType.DEPENDENCY_RISK,
                severity="HIGH",
                title="Circular Dependency Detected",
                description=f"Circular dependency chain: {' → '.join(cycle)}",
                affected_components=cycle,
                evidence=[f"Graph traversal detected cycle at: {cycle[0]}"],
                recommendation="Review architecture to break dependency cycle"
            ))

        # Find deeply nested dependencies (depth > 5)
        deep_chains = self._find_deep_chains(max_depth=5)
        for chain in deep_chains:
            findings.append(RiskFinding(
                finding_id=f"dep_deep_{hashlib.sha256(chain[0].encode()).hexdigest()[:8]}",
                analysis_type=AnalysisType.DEPENDENCY_RISK,
                severity="MEDIUM",
                title="Deep Dependency Chain",
                description=f"Dependency chain depth {len(chain)}: {chain[0]} → ... → {chain[-1]}",
                affected_components=chain,
                evidence=[f"Chain length: {len(chain)} (threshold: 5)"],
                recommendation="Consider flattening or abstracting intermediate layers"
            ))

        # Find orphaned nodes (no dependents, not a root)
        orphans = self._find_orphan_nodes()
        if orphans:
            findings.append(RiskFinding(
                finding_id="dep_orphans",
                analysis_type=AnalysisType.DEPENDENCY_RISK,
                severity="LOW",
                title="Orphaned Components Detected",
                description=f"{len(orphans)} components have no dependents",
                affected_components=orphans[:20],
                evidence=[f"Total orphans: {len(orphans)}"],
                recommendation="Review if these components are still needed"
            ))

        return findings

    def _detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies in graph."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node_id: str, path: List[str]) -> Optional[List[str]]:
            if node_id in rec_stack:
                # Found cycle
                cycle_start = path.index(node_id)
                return path[cycle_start:] + [node_id]

            if node_id in visited:
                return None

            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            node = self.graph.get_node(node_id)
            if node:
                for dep_id in node.dependencies:
                    cycle = dfs(dep_id, path.copy())
                    if cycle:
                        cycles.append(cycle)

            rec_stack.discard(node_id)
            return None

        for node_id in self.graph.nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles[:10]  # Limit output

    def _find_deep_chains(self, max_depth: int) -> List[List[str]]:
        """Find dependency chains deeper than max_depth."""
        deep_chains = []

        def get_max_depth(node_id: str, current_path: List[str]) -> int:
            if node_id in current_path:
                return len(current_path)  # Cycle

            node = self.graph.get_node(node_id)
            if not node or not node.dependencies:
                return len(current_path)

            max_d = len(current_path)
            for dep_id in node.dependencies:
                d = get_max_depth(dep_id, current_path + [node_id])
                if d > max_d:
                    max_d = d

            return max_d

        for node_id in self.graph.nodes:
            node = self.graph.get_node(node_id)
            if node and not node.dependents:  # Start from roots
                depth = get_max_depth(node_id, [])
                if depth > max_depth:
                    deep_chains.append([node_id])

        return deep_chains[:10]

    def _find_orphan_nodes(self) -> List[str]:
        """Find nodes with no dependents."""
        orphans = []
        for node_id, node in self.graph.nodes.items():
            if not node.dependents and node.dependencies:
                orphans.append(node_id)
        return orphans

    # =========================================================================
    # VERSION CONFLICT ANALYSIS
    # =========================================================================

    def analyze_version_conflicts(self) -> List[RiskFinding]:
        """
        Analyze for version conflicts and compatibility issues.
        READ-ONLY operation.
        """
        findings = []

        # Group doctrines by category/technology
        by_tech: Dict[str, List[EngineeringDoctrine]] = defaultdict(list)
        for doctrine in self.doctrines.values():
            if doctrine.version_metadata and doctrine.version_metadata.version_introduced:
                category = doctrine.category or "unknown"
                by_tech[category].append(doctrine)

        # Check for version mismatches within same technology
        for tech, docs in by_tech.items():
            versions = set()
            for doc in docs:
                if doc.version_metadata and doc.version_metadata.version_introduced:
                    versions.add(doc.version_metadata.version_introduced)

            if len(versions) > 3:  # Multiple versions in use
                findings.append(RiskFinding(
                    finding_id=f"ver_mismatch_{tech}",
                    analysis_type=AnalysisType.VERSION_CONFLICT,
                    severity="MEDIUM",
                    title=f"Multiple Versions in {tech}",
                    description=f"{len(versions)} different versions detected: {sorted(versions)[:5]}",
                    affected_components=[d.doctrine_id for d in docs[:10]],
                    evidence=[f"Versions: {sorted(versions)[:5]}"],
                    recommendation="Standardize on a single version where possible"
                ))

        return findings

    # =========================================================================
    # HIDDEN ORCHESTRATOR DETECTION
    # =========================================================================

    def detect_hidden_orchestrators(self) -> List[RiskFinding]:
        """
        Identify hidden orchestrators - components that control many others
        but aren't explicitly marked as orchestrators.
        READ-ONLY operation.
        """
        findings = []

        # Find nodes with high dependent count
        high_impact_nodes = []
        for node_id, node in self.graph.nodes.items():
            dependent_count = len(node.dependents)
            if dependent_count >= 5:  # High impact threshold
                high_impact_nodes.append((node_id, node, dependent_count))

        high_impact_nodes.sort(key=lambda x: x[2], reverse=True)

        for node_id, node, count in high_impact_nodes[:10]:
            # Check if it's marked as an orchestrator
            is_marked = node.metadata.get("is_orchestrator", False)
            if not is_marked and count >= 5:
                findings.append(RiskFinding(
                    finding_id=f"hidden_orch_{node_id[:8]}",
                    analysis_type=AnalysisType.HIDDEN_ORCHESTRATOR,
                    severity="MEDIUM",
                    title=f"Hidden Orchestrator: {node.name}",
                    description=f"{node.name} controls {count} components but isn't marked as orchestrator",
                    affected_components=[node_id] + node.dependents[:10],
                    evidence=[f"Dependent count: {count}", f"Type: {node.node_type}"],
                    recommendation="Review if this should be designated as a formal orchestrator"
                ))

        return findings

    # =========================================================================
    # ARCHITECTURAL CONTRADICTION ANALYSIS
    # =========================================================================

    def analyze_architectural_contradictions(self) -> List[RiskFinding]:
        """
        Find architectural contradictions - conflicting patterns or approaches.
        READ-ONLY operation.
        """
        findings = []

        # Check for conflicting authority claims
        by_topic: Dict[str, List[EngineeringDoctrine]] = defaultdict(list)
        for doctrine in self.doctrines.values():
            topic = doctrine.title.lower()[:30]
            by_topic[topic].append(doctrine)

        for topic, docs in by_topic.items():
            if len(docs) > 1:
                # Check for authority conflicts
                authorities = [d.authority_weight for d in docs]
                if len(set(authorities)) > 1 and max(authorities) - min(authorities) > 40:
                    findings.append(RiskFinding(
                        finding_id=f"arch_conflict_{topic[:8]}",
                        analysis_type=AnalysisType.ARCHITECTURAL_CONTRADICTION,
                        severity="HIGH",
                        title=f"Authority Conflict: {topic[:40]}",
                        description=f"Multiple doctrines with conflicting authority: {sorted(authorities)}",
                        affected_components=[d.doctrine_id for d in docs],
                        evidence=[f"Authority range: {min(authorities)} to {max(authorities)}"],
                        recommendation="Resolve authority conflict - higher authority should win"
                    ))

        return findings

    # =========================================================================
    # DEPRECATION EXPOSURE ANALYSIS
    # =========================================================================

    def analyze_deprecation_exposure(self) -> List[RiskFinding]:
        """
        Identify components exposed to deprecation risk.
        READ-ONLY operation.
        """
        findings = []

        deprecated_docs = []
        removed_docs = []
        eol_soon = []

        for doctrine in self.doctrines.values():
            if not doctrine.version_metadata:
                continue

            status = doctrine.version_metadata.status
            if status == VersionStatus.DEPRECATED:
                deprecated_docs.append(doctrine)
            elif status == VersionStatus.REMOVED:
                removed_docs.append(doctrine)
            elif status == VersionStatus.END_OF_LIFE:
                eol_soon.append(doctrine)

        if deprecated_docs:
            findings.append(RiskFinding(
                finding_id="deprecation_exposure",
                analysis_type=AnalysisType.DEPRECATION_EXPOSURE,
                severity="HIGH",
                title=f"{len(deprecated_docs)} Deprecated Components",
                description="Active dependencies on deprecated APIs/features",
                affected_components=[d.doctrine_id for d in deprecated_docs[:20]],
                evidence=[f"Deprecated: {d.title}" for d in deprecated_docs[:5]],
                recommendation="Plan migration to replacement APIs"
            ))

        if removed_docs:
            findings.append(RiskFinding(
                finding_id="removed_exposure",
                analysis_type=AnalysisType.DEPRECATION_EXPOSURE,
                severity="CRITICAL",
                title=f"{len(removed_docs)} Removed Components Still Referenced",
                description="References to removed APIs/features - BREAKING",
                affected_components=[d.doctrine_id for d in removed_docs[:20]],
                evidence=[f"Removed: {d.title}" for d in removed_docs[:5]],
                recommendation="IMMEDIATE: Remove references to deleted APIs"
            ))

        return findings

    # =========================================================================
    # AUTHORITY COLLISION ANALYSIS
    # =========================================================================

    def analyze_authority_collisions(self) -> List[RiskFinding]:
        """
        Detect authority collisions - multiple sources claiming authority.
        READ-ONLY operation.
        """
        findings = []

        # Group by similar content/topic
        content_hashes: Dict[str, List[EngineeringDoctrine]] = defaultdict(list)
        for doctrine in self.doctrines.values():
            # Create a rough topic hash
            words = set(doctrine.title.lower().split()[:5])
            topic_key = "_".join(sorted(words))
            content_hashes[topic_key].append(doctrine)

        for topic, docs in content_hashes.items():
            if len(docs) > 1:
                # Check for different controlling sources
                sources = set()
                for doc in docs:
                    cs = doc.get_controlling_source()
                    if cs:
                        sources.add(cs.vendor or cs.source_id)

                if len(sources) > 1:
                    findings.append(RiskFinding(
                        finding_id=f"auth_collision_{topic[:8]}",
                        analysis_type=AnalysisType.AUTHORITY_COLLISION,
                        severity="MEDIUM",
                        title="Multiple Authority Sources",
                        description=f"Topic '{topic}' has {len(sources)} different authorities: {sources}",
                        affected_components=[d.doctrine_id for d in docs],
                        evidence=[f"Sources: {sources}"],
                        recommendation="Consolidate to single authoritative source"
                    ))

        return findings

    # =========================================================================
    # FRAGMENTATION VECTOR ANALYSIS
    # =========================================================================

    def analyze_fragmentation_vectors(self) -> List[RiskFinding]:
        """
        Identify fragmentation vectors - areas of architectural divergence.
        READ-ONLY operation.
        """
        findings = []

        # Check graph for disconnected components
        visited = set()
        components = []

        def bfs(start: str) -> Set[str]:
            component = set()
            queue = [start]
            while queue:
                node_id = queue.pop(0)
                if node_id in component:
                    continue
                component.add(node_id)
                node = self.graph.get_node(node_id)
                if node:
                    queue.extend(node.dependencies)
                    queue.extend(node.dependents)
            return component

        for node_id in self.graph.nodes:
            if node_id not in visited:
                component = bfs(node_id)
                visited.update(component)
                components.append(component)

        if len(components) > 3:
            findings.append(RiskFinding(
                finding_id="fragmentation_components",
                analysis_type=AnalysisType.FRAGMENTATION_VECTOR,
                severity="HIGH",
                title=f"Architectural Fragmentation: {len(components)} Isolated Groups",
                description="System has multiple disconnected component groups",
                affected_components=[list(c)[0] for c in components[:10]],
                evidence=[f"Component sizes: {[len(c) for c in components[:10]]}"],
                recommendation="Review if fragmentation is intentional or indicates missing connections"
            ))

        # Check for category fragmentation
        categories = defaultdict(int)
        for doctrine in self.doctrines.values():
            categories[doctrine.category or "unknown"] += 1

        if len(categories) > 20:
            findings.append(RiskFinding(
                finding_id="fragmentation_categories",
                analysis_type=AnalysisType.FRAGMENTATION_VECTOR,
                severity="MEDIUM",
                title=f"Category Fragmentation: {len(categories)} Categories",
                description="Too many doctrine categories may indicate lack of taxonomy",
                affected_components=list(categories.keys())[:20],
                evidence=[f"Top categories: {dict(sorted(categories.items(), key=lambda x: -x[1])[:10])}"],
                recommendation="Consider consolidating categories"
            ))

        return findings

    # =========================================================================
    # COMPLETE BRIEFING GENERATION
    # =========================================================================

    def generate_architectural_briefing(
        self,
        scope: str = "FULL"
    ) -> ArchitecturalBriefing:
        """
        Generate complete architectural briefing.
        READ-ONLY operation. No mutations.
        """
        logger.info(f"Generating architectural briefing (scope: {scope})")

        all_findings = []

        # Run all analyses
        all_findings.extend(self.analyze_dependency_risks())
        all_findings.extend(self.analyze_version_conflicts())
        all_findings.extend(self.detect_hidden_orchestrators())
        all_findings.extend(self.analyze_architectural_contradictions())
        all_findings.extend(self.analyze_deprecation_exposure())
        all_findings.extend(self.analyze_authority_collisions())
        all_findings.extend(self.analyze_fragmentation_vectors())

        # Calculate risk score
        severity_weights = {
            "CRITICAL": 10,
            "HIGH": 5,
            "MEDIUM": 2,
            "LOW": 1,
            "INFO": 0.5
        }
        total_weight = sum(severity_weights.get(f.severity, 1) for f in all_findings)
        risk_score = min(total_weight / 10, 10.0)  # Normalize to 0-10

        # Generate summary
        summary = {
            "total_findings": len(all_findings),
            "by_severity": {
                sev: len([f for f in all_findings if f.severity == sev])
                for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
            },
            "by_type": {
                AnalysisType.DEPENDENCY_RISK: len([f for f in all_findings if f.analysis_type == AnalysisType.DEPENDENCY_RISK]),
                AnalysisType.VERSION_CONFLICT: len([f for f in all_findings if f.analysis_type == AnalysisType.VERSION_CONFLICT]),
                AnalysisType.HIDDEN_ORCHESTRATOR: len([f for f in all_findings if f.analysis_type == AnalysisType.HIDDEN_ORCHESTRATOR]),
                AnalysisType.ARCHITECTURAL_CONTRADICTION: len([f for f in all_findings if f.analysis_type == AnalysisType.ARCHITECTURAL_CONTRADICTION]),
                AnalysisType.DEPRECATION_EXPOSURE: len([f for f in all_findings if f.analysis_type == AnalysisType.DEPRECATION_EXPOSURE]),
                AnalysisType.AUTHORITY_COLLISION: len([f for f in all_findings if f.analysis_type == AnalysisType.AUTHORITY_COLLISION]),
                AnalysisType.FRAGMENTATION_VECTOR: len([f for f in all_findings if f.analysis_type == AnalysisType.FRAGMENTATION_VECTOR])
            },
            "graph_stats": self.graph.get_statistics(),
            "doctrine_count": len(self.doctrines)
        }

        # Generate recommendations
        recommendations = []
        critical_findings = [f for f in all_findings if f.severity == "CRITICAL"]
        high_findings = [f for f in all_findings if f.severity == "HIGH"]

        if critical_findings:
            recommendations.append(f"IMMEDIATE: Address {len(critical_findings)} CRITICAL findings")
        if high_findings:
            recommendations.append(f"PRIORITY: Review {len(high_findings)} HIGH severity findings")
        if risk_score > 7:
            recommendations.append("RISK SCORE HIGH: Consider architectural review")

        briefing = ArchitecturalBriefing(
            briefing_id=f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            scope=scope,
            findings=all_findings,
            summary=summary,
            risk_score=risk_score,
            recommendations=recommendations
        )

        # Cache (read-only, no write to external systems)
        self._analysis_cache[briefing.briefing_id] = briefing

        logger.info(f"Briefing complete: {len(all_findings)} findings, risk score: {risk_score:.1f}")

        return briefing

    def export_briefing(self, briefing: ArchitecturalBriefing) -> Dict[str, Any]:
        """Export briefing to serializable format. READ-ONLY."""
        return {
            "briefing_id": briefing.briefing_id,
            "generated_at": briefing.generated_at.isoformat(),
            "scope": briefing.scope,
            "risk_score": briefing.risk_score,
            "summary": briefing.summary,
            "recommendations": briefing.recommendations,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "type": f.analysis_type,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "affected_components": f.affected_components[:10],
                    "recommendation": f.recommendation
                }
                for f in briefing.findings
            ],
            "observer_state": {
                "mutation_engine": "OFF",
                "autonomous_refactor": "DISABLED",
                "mode": "ENGINEERING_OBSERVER_STATE"
            }
        }
