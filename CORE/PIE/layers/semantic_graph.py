"""
PROGRAMMING INTELLIGENCE ENGINE - LAYER 3
Semantic Engineering Graph

DO NOT store documents as blobs.
Construct a dependency graph linking:

API → Auth Model → SDK → Language Runtime → Infrastructure

Example reasoning capability:
"This OAuth flow is valid only for Google Identity v2.
v3 requires PKCE.
Migration recommended."

That is institutional-grade cognition.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Generator
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
import hashlib
from loguru import logger

from ..engine.models import (
    GraphNode,
    EngineeringDoctrine,
    VersionStatus
)


class NodeType:
    """Standard node types in the engineering graph."""
    API = "API"
    SDK = "SDK"
    LANGUAGE = "LANGUAGE"
    RUNTIME = "RUNTIME"
    FRAMEWORK = "FRAMEWORK"
    LIBRARY = "LIBRARY"
    AUTH_MODEL = "AUTH_MODEL"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    PROTOCOL = "PROTOCOL"
    PATTERN = "PATTERN"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    TOOL = "TOOL"
    PLATFORM = "PLATFORM"


@dataclass
class GraphEdge:
    """Edge connecting two nodes with relationship metadata."""
    source_id: str
    target_id: str
    relationship: str  # DEPENDS_ON, IMPLEMENTS, USES, REQUIRES, etc.
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    version_constraints: Optional[str] = None


@dataclass
class ReasoningPath:
    """A path through the graph representing a reasoning chain."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_weight: float
    reasoning: str
    implications: List[str] = field(default_factory=list)


class SemanticEngineeringGraph:
    """
    LAYER 3: Semantic Engineering Graph

    Constructs a dependency graph linking all engineering concepts.
    Enables institutional-grade reasoning across the entire ecosystem.
    """

    # Standard relationship types
    RELATIONSHIPS = {
        "DEPENDS_ON": 1.0,      # Hard dependency
        "REQUIRES": 0.9,        # Required for functionality
        "IMPLEMENTS": 0.8,      # Implementation of a specification
        "USES": 0.7,            # Uses but not strictly required
        "COMPATIBLE_WITH": 0.6, # Works with
        "EXTENDS": 0.8,         # Extends functionality
        "REPLACES": 0.9,        # Successor/replacement
        "DEPRECATED_BY": 1.0,   # Deprecation relationship
        "AUTHENTICATED_BY": 0.9, # Auth relationship
        "HOSTED_ON": 0.7,       # Hosting relationship
        "COMMUNICATES_WITH": 0.6  # Network communication
    }

    def __init__(self, persist_path: Optional[Path] = None):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self.type_index: Dict[str, Set[str]] = defaultdict(set)
        self.persist_path = persist_path

        logger.info("Semantic Engineering Graph initialized")

    def add_node(self, node: GraphNode) -> GraphNode:
        """Add a node to the graph."""
        if node.node_id in self.nodes:
            # Merge with existing node
            existing = self.nodes[node.node_id]
            existing.dependencies = list(set(existing.dependencies + node.dependencies))
            existing.dependents = list(set(existing.dependents + node.dependents))
            existing.metadata.update(node.metadata)
            return existing

        self.nodes[node.node_id] = node
        self.type_index[node.node_type].add(node.node_id)
        logger.debug(f"Added graph node: {node.node_id} ({node.node_type})")
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: Optional[float] = None,
        metadata: Optional[Dict] = None,
        version_constraints: Optional[str] = None
    ) -> GraphEdge:
        """Add an edge (relationship) between nodes."""
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError(f"Both nodes must exist: {source_id}, {target_id}")

        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight or self.RELATIONSHIPS.get(relationship, 0.5),
            metadata=metadata or {},
            version_constraints=version_constraints
        )

        self.edges.append(edge)
        self.adjacency[source_id].append(target_id)
        self.reverse_adjacency[target_id].append(source_id)

        # Update node relationships
        self.nodes[source_id].add_dependency(target_id)
        self.nodes[target_id].add_dependent(source_id)

        logger.debug(f"Added edge: {source_id} --{relationship}--> {target_id}")
        return edge

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """Get all nodes of a specific type."""
        node_ids = self.type_index.get(node_type, set())
        return [self.nodes[nid] for nid in node_ids]

    def get_dependencies(
        self,
        node_id: str,
        depth: int = 1,
        relationship_filter: Optional[Set[str]] = None
    ) -> List[GraphNode]:
        """
        Get all dependencies of a node up to a certain depth.
        """
        if node_id not in self.nodes:
            return []

        visited = set()
        result = []

        def traverse(current_id: str, current_depth: int):
            if current_depth > depth or current_id in visited:
                return
            visited.add(current_id)

            for target_id in self.adjacency[current_id]:
                # Check relationship filter
                if relationship_filter:
                    matching_edges = [
                        e for e in self.edges
                        if e.source_id == current_id and
                           e.target_id == target_id and
                           e.relationship in relationship_filter
                    ]
                    if not matching_edges:
                        continue

                if target_id not in visited and target_id in self.nodes:
                    result.append(self.nodes[target_id])
                    traverse(target_id, current_depth + 1)

        traverse(node_id, 0)
        return result

    def get_dependents(
        self,
        node_id: str,
        depth: int = 1
    ) -> List[GraphNode]:
        """Get all nodes that depend on this node."""
        if node_id not in self.nodes:
            return []

        visited = set()
        result = []

        def traverse(current_id: str, current_depth: int):
            if current_depth > depth or current_id in visited:
                return
            visited.add(current_id)

            for source_id in self.reverse_adjacency[current_id]:
                if source_id not in visited and source_id in self.nodes:
                    result.append(self.nodes[source_id])
                    traverse(source_id, current_depth + 1)

        traverse(node_id, 0)
        return result

    def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 10
    ) -> Optional[ReasoningPath]:
        """
        Find a path between two nodes using BFS.
        Returns the reasoning path with all relationships.
        """
        if start_id not in self.nodes or end_id not in self.nodes:
            return None

        from collections import deque

        queue = deque([(start_id, [start_id], [])])
        visited = {start_id}

        while queue:
            current, path, edges = queue.popleft()

            if current == end_id:
                # Build the reasoning path
                nodes = [self.nodes[nid] for nid in path]
                total_weight = sum(e.weight for e in edges) if edges else 0

                reasoning = self._build_reasoning_chain(nodes, edges)
                implications = self._derive_implications(nodes, edges)

                return ReasoningPath(
                    nodes=nodes,
                    edges=edges,
                    total_weight=total_weight,
                    reasoning=reasoning,
                    implications=implications
                )

            if len(path) >= max_depth:
                continue

            for neighbor_id in self.adjacency[current]:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    # Find the edge
                    edge = next(
                        (e for e in self.edges
                         if e.source_id == current and e.target_id == neighbor_id),
                        None
                    )
                    new_edges = edges + ([edge] if edge else [])
                    queue.append((neighbor_id, path + [neighbor_id], new_edges))

        return None

    def _build_reasoning_chain(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> str:
        """Build a human-readable reasoning chain."""
        if len(nodes) < 2:
            return f"Single node: {nodes[0].name}" if nodes else "Empty path"

        parts = []
        for i, node in enumerate(nodes):
            if i > 0 and i - 1 < len(edges):
                edge = edges[i - 1]
                parts.append(f"--[{edge.relationship}]-->")
            parts.append(f"{node.name} ({node.node_type})")

        return " ".join(parts)

    def _derive_implications(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> List[str]:
        """Derive implications from a reasoning path."""
        implications = []

        for edge in edges:
            if edge.relationship == "DEPRECATED_BY":
                target = self.nodes.get(edge.target_id)
                if target:
                    implications.append(
                        f"Migration recommended: Use {target.name} instead"
                    )
            elif edge.relationship == "REQUIRES":
                target = self.nodes.get(edge.target_id)
                if target and edge.version_constraints:
                    implications.append(
                        f"Version constraint: {target.name} {edge.version_constraints}"
                    )
            elif edge.relationship == "AUTHENTICATED_BY":
                target = self.nodes.get(edge.target_id)
                if target:
                    implications.append(
                        f"Authentication: Requires {target.name} setup"
                    )

        return implications

    def analyze_impact(
        self,
        node_id: str,
        change_type: str = "DEPRECATION"
    ) -> Dict[str, Any]:
        """
        Analyze the impact of a change to a node.
        What else is affected if this node changes?
        """
        if node_id not in self.nodes:
            return {"error": f"Node not found: {node_id}"}

        node = self.nodes[node_id]
        dependents = self.get_dependents(node_id, depth=5)

        impact = {
            "changed_node": {
                "id": node.node_id,
                "name": node.name,
                "type": node.node_type
            },
            "change_type": change_type,
            "total_affected": len(dependents),
            "affected_by_type": {},
            "affected_nodes": [],
            "critical_paths": [],
            "recommendations": []
        }

        # Group by type
        type_counts = defaultdict(int)
        for dep in dependents:
            type_counts[dep.node_type] += 1
            impact["affected_nodes"].append({
                "id": dep.node_id,
                "name": dep.name,
                "type": dep.node_type
            })

        impact["affected_by_type"] = dict(type_counts)

        # Find critical paths (high-weight dependencies)
        for dep in dependents:
            path = self.find_path(dep.node_id, node_id)
            if path and path.total_weight >= 2.0:
                impact["critical_paths"].append({
                    "from": dep.name,
                    "reasoning": path.reasoning,
                    "weight": path.total_weight
                })

        # Generate recommendations
        if change_type == "DEPRECATION":
            impact["recommendations"].append(
                f"Create migration guide for {len(dependents)} dependent components"
            )
            if impact["critical_paths"]:
                impact["recommendations"].append(
                    "PRIORITY: Address critical path dependencies first"
                )
        elif change_type == "REMOVAL":
            impact["recommendations"].append(
                f"CRITICAL: {len(dependents)} components will break"
            )
            impact["recommendations"].append(
                "Update all dependents before removal"
            )

        return impact

    def reason_about(
        self,
        query: str,
        context_nodes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Reason about an engineering question using the graph.
        This is the core reasoning method.
        """
        # Find relevant nodes based on query keywords
        relevant_nodes = self._find_relevant_nodes(query)

        if context_nodes:
            relevant_nodes.extend([
                self.nodes[nid] for nid in context_nodes
                if nid in self.nodes
            ])

        if not relevant_nodes:
            return {
                "query": query,
                "result": "No relevant nodes found",
                "confidence": 0.0
            }

        # Build reasoning paths between relevant nodes
        reasoning_chains = []
        for i, node1 in enumerate(relevant_nodes):
            for node2 in relevant_nodes[i+1:]:
                path = self.find_path(node1.node_id, node2.node_id)
                if path:
                    reasoning_chains.append(path)

        # Analyze dependencies
        all_deps = []
        for node in relevant_nodes:
            deps = self.get_dependencies(node.node_id, depth=2)
            all_deps.extend(deps)

        # Build response
        response = {
            "query": query,
            "relevant_nodes": [
                {"id": n.node_id, "name": n.name, "type": n.node_type}
                for n in relevant_nodes
            ],
            "reasoning_chains": [
                {
                    "path": path.reasoning,
                    "implications": path.implications,
                    "weight": path.total_weight
                }
                for path in reasoning_chains
            ],
            "dependencies": [
                {"id": d.node_id, "name": d.name, "type": d.node_type}
                for d in all_deps[:20]  # Limit output
            ],
            "insights": self._generate_insights(relevant_nodes, reasoning_chains),
            "confidence": self._calculate_reasoning_confidence(
                relevant_nodes, reasoning_chains
            )
        }

        return response

    def _find_relevant_nodes(self, query: str) -> List[GraphNode]:
        """Find nodes relevant to a query."""
        query_lower = query.lower()
        words = set(query_lower.split())

        scored_nodes = []
        for node in self.nodes.values():
            score = 0
            name_lower = node.name.lower()

            # Direct name match
            if name_lower in query_lower:
                score += 10
            # Word overlap
            name_words = set(name_lower.replace("-", " ").replace("_", " ").split())
            overlap = words & name_words
            score += len(overlap) * 2

            # Type match
            if node.node_type.lower() in query_lower:
                score += 3

            if score > 0:
                scored_nodes.append((score, node))

        scored_nodes.sort(reverse=True, key=lambda x: x[0])
        return [node for _, node in scored_nodes[:10]]

    def _generate_insights(
        self,
        nodes: List[GraphNode],
        paths: List[ReasoningPath]
    ) -> List[str]:
        """Generate insights from the analysis."""
        insights = []

        # Check for version mismatches
        versions = {}
        for node in nodes:
            if node.version:
                if node.node_type in versions:
                    if node.version != versions[node.node_type]:
                        insights.append(
                            f"Version mismatch in {node.node_type}: "
                            f"{versions[node.node_type]} vs {node.version}"
                        )
                versions[node.node_type] = node.version

        # Check for deprecated items in paths
        for path in paths:
            for node in path.nodes:
                if node.metadata.get("status") == "DEPRECATED":
                    insights.append(
                        f"Path includes deprecated component: {node.name}"
                    )

        # Authentication requirements
        auth_nodes = [n for n in nodes if n.node_type == NodeType.AUTH_MODEL]
        if auth_nodes:
            insights.append(
                f"Authentication required: {', '.join(n.name for n in auth_nodes)}"
            )

        return insights

    def _calculate_reasoning_confidence(
        self,
        nodes: List[GraphNode],
        paths: List[ReasoningPath]
    ) -> float:
        """Calculate confidence in the reasoning."""
        if not nodes:
            return 0.0

        # Base confidence from node count
        confidence = min(len(nodes) * 0.1, 0.5)

        # Boost from paths
        if paths:
            confidence += min(len(paths) * 0.1, 0.3)

        # Boost from connected graph
        total_edges = sum(len(n.dependencies) + len(n.dependents) for n in nodes)
        if total_edges > len(nodes):
            confidence += 0.2

        return min(confidence, 1.0)

    def export_graph(self) -> Dict[str, Any]:
        """Export the graph for persistence or visualization."""
        return {
            "nodes": [
                {
                    "id": n.node_id,
                    "type": n.node_type,
                    "name": n.name,
                    "version": n.version,
                    "dependencies": n.dependencies,
                    "metadata": n.metadata
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "relationship": e.relationship,
                    "weight": e.weight,
                    "version_constraints": e.version_constraints
                }
                for e in self.edges
            ],
            "metadata": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "exported_at": datetime.now().isoformat()
            }
        }

    def import_graph(self, data: Dict[str, Any]):
        """Import a graph from exported data."""
        for node_data in data.get("nodes", []):
            node = GraphNode(
                node_id=node_data["id"],
                node_type=node_data["type"],
                name=node_data["name"],
                version=node_data.get("version"),
                dependencies=node_data.get("dependencies", []),
                metadata=node_data.get("metadata", {})
            )
            self.add_node(node)

        for edge_data in data.get("edges", []):
            try:
                self.add_edge(
                    source_id=edge_data["source"],
                    target_id=edge_data["target"],
                    relationship=edge_data["relationship"],
                    weight=edge_data.get("weight"),
                    version_constraints=edge_data.get("version_constraints")
                )
            except ValueError:
                continue  # Skip edges with missing nodes

        logger.info(f"Imported graph: {len(self.nodes)} nodes, {len(self.edges)} edges")

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": {
                ntype: len(nids) for ntype, nids in self.type_index.items()
            },
            "avg_dependencies": (
                sum(len(n.dependencies) for n in self.nodes.values()) /
                len(self.nodes) if self.nodes else 0
            ),
            "most_connected": sorted(
                [(n.node_id, len(n.dependencies) + len(n.dependents))
                 for n in self.nodes.values()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
