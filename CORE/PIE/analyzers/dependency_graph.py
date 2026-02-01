"""
PROGRAMMING INTELLIGENCE ENGINE - Dependency Graph Analyzer
STRUCTURAL RISK IDENTIFICATION

Analyzes dependency graphs to identify:
- SPOFs (Single Points of Failure)
- Cascade risk chains
- Hidden orchestrators
- Circular dependencies
- Fragmentation vectors

READ-ONLY: Does not modify graph structure.
DETERMINISTIC: Same graph → same analysis.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, deque
import hashlib
from loguru import logger

from ..layers.semantic_graph import SemanticEngineeringGraph, GraphNode, NodeType


class RiskLevel(str):
    """Risk level classifications."""
    CRITICAL = "CRITICAL"    # System cannot function
    HIGH = "HIGH"            # Major functionality impacted
    MEDIUM = "MEDIUM"        # Significant but contained
    LOW = "LOW"              # Minor impact
    INFO = "INFO"            # Informational only


@dataclass
class SPOFAnalysis:
    """
    Single Point of Failure analysis result.
    A SPOF is a node whose failure would cascade to many dependents.
    """
    node_id: str
    node_name: str
    node_type: str
    dependent_count: int
    cascade_depth: int
    affected_node_ids: List[str]
    risk_level: str
    mitigation_suggestions: List[str]

    @property
    def risk_score(self) -> float:
        """Compute risk score from 0-10."""
        base = min(self.dependent_count * 0.5, 5.0)
        depth_factor = min(self.cascade_depth * 0.3, 3.0)
        return min(base + depth_factor, 10.0)


@dataclass
class CascadeRisk:
    """
    Cascade risk analysis - chains of dependencies that could fail together.
    """
    trigger_node_id: str
    trigger_name: str
    cascade_chain: List[str]        # Ordered list of affected nodes
    total_affected: int
    max_depth: int
    critical_path: bool             # Whether this affects critical infrastructure
    risk_level: str


@dataclass
class CircularDependency:
    """
    Circular dependency detection result.
    """
    cycle_nodes: List[str]          # Nodes in the cycle
    cycle_names: List[str]          # Names for readability
    cycle_length: int
    severity: str                   # Based on node types in cycle
    break_suggestions: List[str]


@dataclass
class HiddenOrchestrator:
    """
    Hidden orchestrator - a node that controls many others but isn't explicitly marked.
    """
    node_id: str
    node_name: str
    node_type: str
    controlled_count: int
    controlled_types: Dict[str, int]
    is_formally_designated: bool
    recommendation: str


@dataclass
class FragmentationAnalysis:
    """
    Graph fragmentation analysis - disconnected components.
    """
    total_components: int
    component_sizes: List[int]
    largest_component: int
    orphan_nodes: List[str]         # Nodes with no connections
    bridge_nodes: List[str]         # Nodes whose removal fragments the graph
    fragmentation_score: float      # 0 (unified) to 1 (fragmented)


@dataclass
class DependencyGraphReport:
    """
    Complete dependency graph analysis report.
    """
    report_id: str
    generated_at: datetime
    graph_stats: Dict[str, Any]
    spofs: List[SPOFAnalysis]
    cascade_risks: List[CascadeRisk]
    circular_dependencies: List[CircularDependency]
    hidden_orchestrators: List[HiddenOrchestrator]
    fragmentation: FragmentationAnalysis
    overall_risk_score: float
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "graph_stats": self.graph_stats,
            "spof_count": len(self.spofs),
            "cascade_risk_count": len(self.cascade_risks),
            "circular_dependency_count": len(self.circular_dependencies),
            "hidden_orchestrator_count": len(self.hidden_orchestrators),
            "fragmentation_score": self.fragmentation.fragmentation_score,
            "overall_risk_score": self.overall_risk_score,
            "recommendations": self.recommendations
        }


class DependencyGraphAnalyzer:
    """
    DEPENDENCY GRAPH ANALYZER

    READ-ONLY analysis of dependency graphs.
    Identifies structural risks deterministically.

    Does NOT modify the graph - observation only.
    """

    # Thresholds for risk classification
    SPOF_THRESHOLD = 5              # Dependents count for SPOF
    CASCADE_DEPTH_THRESHOLD = 4     # Depth for cascade concern
    ORCHESTRATOR_THRESHOLD = 5      # Controlled nodes for orchestrator

    # Critical node types (higher risk when SPOF)
    CRITICAL_TYPES = {
        NodeType.AUTH_MODEL,
        NodeType.DATABASE,
        NodeType.INFRASTRUCTURE,
        NodeType.SERVICE,
    }

    def __init__(self, graph: SemanticEngineeringGraph):
        self.graph = graph
        self._analysis_cache: Dict[str, DependencyGraphReport] = {}

        logger.info("Dependency Graph Analyzer initialized (READ-ONLY)")

    def analyze(self) -> DependencyGraphReport:
        """
        Run complete dependency graph analysis.
        READ-ONLY operation - does not modify graph.
        """
        logger.info("Starting dependency graph analysis")

        # Compute cache key from graph state
        cache_key = self._compute_graph_hash()
        if cache_key in self._analysis_cache:
            logger.debug("Returning cached analysis")
            return self._analysis_cache[cache_key]

        # Run all analyses
        spofs = self._analyze_spofs()
        cascade_risks = self._analyze_cascade_risks()
        circular_deps = self._detect_circular_dependencies()
        hidden_orch = self._detect_hidden_orchestrators()
        fragmentation = self._analyze_fragmentation()

        # Compute overall risk
        overall_risk = self._compute_overall_risk(
            spofs, cascade_risks, circular_deps, hidden_orch, fragmentation
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            spofs, cascade_risks, circular_deps, hidden_orch, fragmentation
        )

        report = DependencyGraphReport(
            report_id=f"dep_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            graph_stats=self.graph.get_statistics(),
            spofs=spofs,
            cascade_risks=cascade_risks,
            circular_dependencies=circular_deps,
            hidden_orchestrators=hidden_orch,
            fragmentation=fragmentation,
            overall_risk_score=overall_risk,
            recommendations=recommendations
        )

        self._analysis_cache[cache_key] = report

        logger.info(
            f"Analysis complete: {len(spofs)} SPOFs, {len(cascade_risks)} cascade risks, "
            f"{len(circular_deps)} cycles, risk score: {overall_risk:.1f}"
        )

        return report

    def _compute_graph_hash(self) -> str:
        """Compute deterministic hash of graph state."""
        node_ids = sorted(self.graph.nodes.keys())
        edge_strs = sorted([
            f"{e.source_id}->{e.target_id}" for e in self.graph.edges
        ])
        content = f"{node_ids}{edge_strs}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _analyze_spofs(self) -> List[SPOFAnalysis]:
        """
        Identify Single Points of Failure.
        A SPOF is a node that many other nodes depend on.
        """
        spofs = []

        for node_id, node in self.graph.nodes.items():
            dependent_count = len(node.dependents)

            if dependent_count >= self.SPOF_THRESHOLD:
                # Calculate cascade depth
                cascade_depth = self._calculate_cascade_depth(node_id)

                # Get all affected nodes
                affected = self._get_all_dependents(node_id)

                # Determine risk level
                risk_level = self._classify_spof_risk(
                    node, dependent_count, cascade_depth
                )

                # Generate mitigations
                mitigations = self._suggest_spof_mitigations(node)

                spofs.append(SPOFAnalysis(
                    node_id=node_id,
                    node_name=node.name,
                    node_type=node.node_type,
                    dependent_count=dependent_count,
                    cascade_depth=cascade_depth,
                    affected_node_ids=list(affected)[:50],
                    risk_level=risk_level,
                    mitigation_suggestions=mitigations
                ))

        # Sort by risk
        spofs.sort(key=lambda s: s.risk_score, reverse=True)
        return spofs[:20]  # Top 20

    def _calculate_cascade_depth(self, node_id: str) -> int:
        """Calculate the maximum depth of cascade from a node."""
        visited = set()
        max_depth = 0

        def dfs(current_id: str, depth: int):
            nonlocal max_depth
            if current_id in visited:
                return
            visited.add(current_id)
            max_depth = max(max_depth, depth)

            node = self.graph.get_node(current_id)
            if node:
                for dependent_id in node.dependents:
                    dfs(dependent_id, depth + 1)

        dfs(node_id, 0)
        return max_depth

    def _get_all_dependents(self, node_id: str, max_depth: int = 10) -> Set[str]:
        """Get all nodes that depend on this node (recursively)."""
        dependents = set()
        queue = deque([(node_id, 0)])
        visited = {node_id}

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            node = self.graph.get_node(current_id)
            if node:
                for dep_id in node.dependents:
                    if dep_id not in visited:
                        visited.add(dep_id)
                        dependents.add(dep_id)
                        queue.append((dep_id, depth + 1))

        return dependents

    def _classify_spof_risk(
        self,
        node: GraphNode,
        dependent_count: int,
        cascade_depth: int
    ) -> str:
        """Classify SPOF risk level."""
        is_critical_type = node.node_type in self.CRITICAL_TYPES

        if dependent_count >= 20 or (is_critical_type and dependent_count >= 10):
            return RiskLevel.CRITICAL
        elif dependent_count >= 10 or cascade_depth >= 5:
            return RiskLevel.HIGH
        elif dependent_count >= 5:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _suggest_spof_mitigations(self, node: GraphNode) -> List[str]:
        """Suggest mitigations for a SPOF."""
        suggestions = []

        if node.node_type == NodeType.DATABASE:
            suggestions.append("Implement database replication or clustering")
            suggestions.append("Add read replicas for read-heavy workloads")
        elif node.node_type == NodeType.AUTH_MODEL:
            suggestions.append("Implement redundant authentication providers")
            suggestions.append("Add fallback authentication mechanism")
        elif node.node_type == NodeType.SERVICE:
            suggestions.append("Deploy multiple service instances behind load balancer")
            suggestions.append("Implement circuit breakers for dependent services")
        elif node.node_type == NodeType.INFRASTRUCTURE:
            suggestions.append("Use multi-AZ or multi-region deployment")
            suggestions.append("Implement infrastructure redundancy")

        suggestions.append(f"Consider abstracting {node.name} behind an interface")
        suggestions.append("Add health checks and monitoring")

        return suggestions

    def _analyze_cascade_risks(self) -> List[CascadeRisk]:
        """
        Analyze cascade failure risks.
        Identifies chains where one failure triggers many others.
        """
        risks = []

        # Find root nodes (no dependencies themselves)
        root_nodes = [
            node_id for node_id, node in self.graph.nodes.items()
            if not node.dependencies
        ]

        for root_id in root_nodes:
            cascade = self._trace_cascade(root_id)
            if len(cascade) >= self.CASCADE_DEPTH_THRESHOLD:
                node = self.graph.get_node(root_id)
                max_depth = self._calculate_cascade_depth(root_id)

                # Check if critical infrastructure is in cascade
                critical_path = any(
                    self.graph.get_node(nid) and
                    self.graph.get_node(nid).node_type in self.CRITICAL_TYPES
                    for nid in cascade
                )

                risk_level = RiskLevel.CRITICAL if critical_path else RiskLevel.HIGH

                risks.append(CascadeRisk(
                    trigger_node_id=root_id,
                    trigger_name=node.name if node else root_id,
                    cascade_chain=cascade[:20],
                    total_affected=len(cascade),
                    max_depth=max_depth,
                    critical_path=critical_path,
                    risk_level=risk_level
                ))

        risks.sort(key=lambda r: r.total_affected, reverse=True)
        return risks[:10]

    def _trace_cascade(self, start_id: str) -> List[str]:
        """Trace the cascade path from a starting node."""
        cascade = []
        visited = set()
        queue = deque([start_id])

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            cascade.append(node_id)

            node = self.graph.get_node(node_id)
            if node:
                for dep_id in node.dependents:
                    if dep_id not in visited:
                        queue.append(dep_id)

        return cascade

    def _detect_circular_dependencies(self) -> List[CircularDependency]:
        """
        Detect circular dependencies in the graph.
        Uses DFS-based cycle detection.
        """
        cycles = []
        visited = set()
        rec_stack = set()
        found_cycles: Set[frozenset] = set()

        def dfs(node_id: str, path: List[str]) -> None:
            if node_id in rec_stack:
                # Found cycle
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:]
                cycle_set = frozenset(cycle)

                if cycle_set not in found_cycles and len(cycle) >= 2:
                    found_cycles.add(cycle_set)
                    node_names = [
                        self.graph.get_node(nid).name if self.graph.get_node(nid) else nid
                        for nid in cycle
                    ]

                    # Determine severity
                    has_critical = any(
                        self.graph.get_node(nid) and
                        self.graph.get_node(nid).node_type in self.CRITICAL_TYPES
                        for nid in cycle
                    )

                    severity = RiskLevel.CRITICAL if has_critical else RiskLevel.HIGH

                    cycles.append(CircularDependency(
                        cycle_nodes=cycle,
                        cycle_names=node_names,
                        cycle_length=len(cycle),
                        severity=severity,
                        break_suggestions=self._suggest_cycle_breaks(cycle)
                    ))
                return

            if node_id in visited:
                return

            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            node = self.graph.get_node(node_id)
            if node:
                for dep_id in node.dependencies:
                    dfs(dep_id, path.copy())

            rec_stack.discard(node_id)

        for node_id in self.graph.nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles[:10]

    def _suggest_cycle_breaks(self, cycle: List[str]) -> List[str]:
        """Suggest how to break a circular dependency."""
        suggestions = []

        # Find the weakest link (lowest authority type)
        type_priority = [
            NodeType.TOOL,
            NodeType.LIBRARY,
            NodeType.PATTERN,
            NodeType.SERVICE,
            NodeType.FRAMEWORK,
        ]

        for ntype in type_priority:
            for node_id in cycle:
                node = self.graph.get_node(node_id)
                if node and node.node_type == ntype:
                    suggestions.append(
                        f"Consider extracting {node.name} to break the cycle"
                    )
                    break
            if suggestions:
                break

        suggestions.append("Introduce dependency injection to decouple components")
        suggestions.append("Create an abstraction layer between cyclic components")

        return suggestions

    def _detect_hidden_orchestrators(self) -> List[HiddenOrchestrator]:
        """
        Detect hidden orchestrators - nodes controlling many others
        without being formally designated as orchestrators.
        """
        orchestrators = []

        for node_id, node in self.graph.nodes.items():
            controlled_count = len(node.dependents)

            if controlled_count >= self.ORCHESTRATOR_THRESHOLD:
                is_designated = node.metadata.get("is_orchestrator", False)

                # Count controlled types
                type_counts: Dict[str, int] = defaultdict(int)
                for dep_id in node.dependents:
                    dep_node = self.graph.get_node(dep_id)
                    if dep_node:
                        type_counts[dep_node.node_type] += 1

                recommendation = (
                    "Already designated as orchestrator" if is_designated
                    else f"Consider formally designating {node.name} as an orchestrator"
                )

                orchestrators.append(HiddenOrchestrator(
                    node_id=node_id,
                    node_name=node.name,
                    node_type=node.node_type,
                    controlled_count=controlled_count,
                    controlled_types=dict(type_counts),
                    is_formally_designated=is_designated,
                    recommendation=recommendation
                ))

        # Sort by control count
        orchestrators.sort(key=lambda o: o.controlled_count, reverse=True)
        return orchestrators[:10]

    def _analyze_fragmentation(self) -> FragmentationAnalysis:
        """
        Analyze graph fragmentation - disconnected components.
        """
        visited = set()
        components: List[Set[str]] = []

        def bfs(start: str) -> Set[str]:
            component = set()
            queue = deque([start])
            while queue:
                node_id = queue.popleft()
                if node_id in component:
                    continue
                component.add(node_id)

                node = self.graph.get_node(node_id)
                if node:
                    for neighbor in node.dependencies + node.dependents:
                        if neighbor not in component and neighbor in self.graph.nodes:
                            queue.append(neighbor)
            return component

        for node_id in self.graph.nodes:
            if node_id not in visited:
                component = bfs(node_id)
                visited.update(component)
                components.append(component)

        component_sizes = sorted([len(c) for c in components], reverse=True)
        largest = component_sizes[0] if component_sizes else 0

        # Find orphan nodes
        orphans = [
            node_id for node_id, node in self.graph.nodes.items()
            if not node.dependencies and not node.dependents
        ]

        # Find bridge nodes (approximation)
        bridges = self._find_bridge_nodes()

        # Compute fragmentation score
        if len(self.graph.nodes) == 0:
            frag_score = 0.0
        else:
            # Score based on how much of graph is in largest component
            coverage = largest / len(self.graph.nodes)
            frag_score = 1.0 - coverage

        return FragmentationAnalysis(
            total_components=len(components),
            component_sizes=component_sizes,
            largest_component=largest,
            orphan_nodes=orphans[:20],
            bridge_nodes=bridges[:20],
            fragmentation_score=frag_score
        )

    def _find_bridge_nodes(self) -> List[str]:
        """
        Find bridge nodes whose removal would fragment the graph.
        Approximate method based on betweenness.
        """
        bridges = []

        for node_id, node in self.graph.nodes.items():
            # A simple heuristic: nodes with both dependencies and dependents
            # that are not otherwise connected
            if node.dependencies and node.dependents:
                # Check if removing this node would disconnect its neighbors
                dep_set = set(node.dependencies)
                dependent_set = set(node.dependents)

                # If there's no path between dependencies and dependents except through this node
                # it's a bridge. This is a simplification.
                if not dep_set.intersection(dependent_set):
                    bridges.append(node_id)

        return bridges

    def _compute_overall_risk(
        self,
        spofs: List[SPOFAnalysis],
        cascade_risks: List[CascadeRisk],
        circular_deps: List[CircularDependency],
        hidden_orch: List[HiddenOrchestrator],
        fragmentation: FragmentationAnalysis
    ) -> float:
        """Compute overall risk score (0-10)."""
        score = 0.0

        # SPOF contribution
        critical_spofs = len([s for s in spofs if s.risk_level == RiskLevel.CRITICAL])
        high_spofs = len([s for s in spofs if s.risk_level == RiskLevel.HIGH])
        score += min(critical_spofs * 1.5 + high_spofs * 0.5, 3.0)

        # Cascade risk contribution
        critical_cascades = len([c for c in cascade_risks if c.critical_path])
        score += min(critical_cascades * 1.0, 2.0)

        # Circular dependency contribution
        score += min(len(circular_deps) * 0.5, 2.0)

        # Hidden orchestrator contribution (lower concern)
        unmarked = len([o for o in hidden_orch if not o.is_formally_designated])
        score += min(unmarked * 0.2, 1.0)

        # Fragmentation contribution
        score += fragmentation.fragmentation_score * 2.0

        return min(score, 10.0)

    def _generate_recommendations(
        self,
        spofs: List[SPOFAnalysis],
        cascade_risks: List[CascadeRisk],
        circular_deps: List[CircularDependency],
        hidden_orch: List[HiddenOrchestrator],
        fragmentation: FragmentationAnalysis
    ) -> List[str]:
        """Generate prioritized recommendations."""
        recommendations = []

        # Critical SPOFs first
        critical_spofs = [s for s in spofs if s.risk_level == RiskLevel.CRITICAL]
        if critical_spofs:
            recommendations.append(
                f"CRITICAL: Address {len(critical_spofs)} single points of failure immediately"
            )
            for spof in critical_spofs[:3]:
                recommendations.append(f"  - {spof.node_name}: {spof.mitigation_suggestions[0]}")

        # Cascade risks
        if cascade_risks:
            recommendations.append(
                f"HIGH: Review {len(cascade_risks)} cascade failure chains"
            )

        # Circular dependencies
        if circular_deps:
            recommendations.append(
                f"HIGH: Resolve {len(circular_deps)} circular dependencies"
            )

        # Fragmentation
        if fragmentation.fragmentation_score > 0.5:
            recommendations.append(
                f"MEDIUM: High fragmentation ({fragmentation.total_components} components) - review architecture"
            )

        # Hidden orchestrators
        unmarked = [o for o in hidden_orch if not o.is_formally_designated]
        if unmarked:
            recommendations.append(
                f"LOW: {len(unmarked)} components acting as orchestrators without designation"
            )

        return recommendations


# Self-test
def _self_test():
    """Validate dependency graph analyzer."""
    from ..layers.semantic_graph import SemanticEngineeringGraph, GraphNode

    # Create test graph
    graph = SemanticEngineeringGraph()

    # Add nodes
    graph.add_node(GraphNode(node_id="auth", node_type=NodeType.AUTH_MODEL, name="Auth Service"))
    graph.add_node(GraphNode(node_id="db", node_type=NodeType.DATABASE, name="Main Database"))
    graph.add_node(GraphNode(node_id="api1", node_type=NodeType.API, name="API Gateway"))
    graph.add_node(GraphNode(node_id="svc1", node_type=NodeType.SERVICE, name="User Service"))
    graph.add_node(GraphNode(node_id="svc2", node_type=NodeType.SERVICE, name="Order Service"))
    graph.add_node(GraphNode(node_id="svc3", node_type=NodeType.SERVICE, name="Payment Service"))
    graph.add_node(GraphNode(node_id="svc4", node_type=NodeType.SERVICE, name="Inventory Service"))
    graph.add_node(GraphNode(node_id="svc5", node_type=NodeType.SERVICE, name="Notification Service"))

    # Add edges (dependencies) - db and auth each have 5+ dependents
    graph.add_edge("api1", "auth", "AUTHENTICATED_BY")
    graph.add_edge("svc1", "db", "DEPENDS_ON")
    graph.add_edge("svc2", "db", "DEPENDS_ON")
    graph.add_edge("svc3", "db", "DEPENDS_ON")
    graph.add_edge("svc4", "db", "DEPENDS_ON")
    graph.add_edge("svc5", "db", "DEPENDS_ON")
    graph.add_edge("svc1", "auth", "AUTHENTICATED_BY")
    graph.add_edge("svc2", "auth", "AUTHENTICATED_BY")
    graph.add_edge("svc3", "auth", "AUTHENTICATED_BY")
    graph.add_edge("svc4", "auth", "AUTHENTICATED_BY")
    graph.add_edge("svc5", "auth", "AUTHENTICATED_BY")

    # Run analysis
    analyzer = DependencyGraphAnalyzer(graph)
    report = analyzer.analyze()

    # Validate (SPOF_THRESHOLD=5, so db and auth should be detected)
    assert len(report.spofs) > 0, "Should detect SPOFs (db and auth have 5+ dependents)"
    assert report.overall_risk_score >= 0, "Should compute risk score"
    assert report.fragmentation.total_components >= 1, "Should count components"

    logger.info("Dependency Graph Analyzer self-test PASSED")


if __name__ == "__main__":
    _self_test()
