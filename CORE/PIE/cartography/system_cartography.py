"""
PIE CARTOGRAPHY ANALYSIS
System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO

Feeds real system artifacts to PIE for engineering analysis.
OBSERVER ONLY - No mutations.
"""

import sys
sys.path.insert(0, "O:/ECHO_OMEGA_PRIME")

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum
from datetime import datetime
import hashlib

from loguru import logger

# Configure logging
logger.add(
    "O:/ECHO_OMEGA_PRIME/logs/pie_cartography.log",
    rotation="10 MB",
    level="INFO"
)


class ServiceStatus(Enum):
    """Runtime status of a service."""
    WORKING = "WORKING"
    NEEDS_INPUT = "NEEDS_INPUT"
    NOT_RUNNING = "NOT_RUNNING"
    NOT_DEPLOYED = "NOT_DEPLOYED"
    UNKNOWN = "UNKNOWN"


class ServiceTier(Enum):
    """Deployment tier of a service."""
    CLOUD_RUN = "CLOUD_RUN"
    LOCAL = "LOCAL"
    LAN = "LAN"
    CLOUD_INFRA = "CLOUD_INFRA"
    MCP = "MCP"


class CriticalityLevel(Enum):
    """Criticality classification."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ServiceNode:
    """Represents a service in the system topology."""
    service_id: str
    name: str
    tier: ServiceTier
    status: ServiceStatus
    port: Optional[int] = None
    host: str = "localhost"
    url: Optional[str] = None
    criticality: CriticalityLevel = CriticalityLevel.MEDIUM
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    authority_level: Optional[float] = None
    documented: bool = True
    has_health_check: bool = False
    can_auto_restart: bool = False
    notes: str = ""


@dataclass
class DependencyEdge:
    """Represents a dependency between services."""
    source_id: str
    target_id: str
    dependency_type: str  # REQUIRES, AUTHENTICATES_WITH, BACKS_UP_TO, etc.
    is_critical: bool = False
    is_documented: bool = True
    failover_exists: bool = False


class SystemCartography:
    """
    Real system topology loaded from cartography artifacts.
    READ-ONLY - Observation only.
    """

    def __init__(self):
        self.services: Dict[str, ServiceNode] = {}
        self.dependencies: List[DependencyEdge] = []
        self.analysis_timestamp = datetime.utcnow().isoformat()

        logger.info("SystemCartography initialized (READ-ONLY)")
        self._load_system_topology()

    def _load_system_topology(self):
        """Load real system topology from status reports."""

        # =========================================================
        # CLOUD RUN SERVICES - WORKING (10)
        # =========================================================
        working_cloud_services = [
            ("citadel", "Security gateway", CriticalityLevel.HIGH),
            ("crystal-memory", "Memory storage", CriticalityLevel.HIGH),
            ("forge", "Build system", CriticalityLevel.MEDIUM),
            ("mega-gateway", "35k+ tools hub", CriticalityLevel.HIGH),
            ("omnipresence-api", "Echo-op.com backend", CriticalityLevel.MEDIUM),
            ("prometheus-prime-api", "Security/OSINT cloud", CriticalityLevel.HIGH),
            ("sentinel-omni", "Monitoring", CriticalityLevel.HIGH),
            ("shadowglass-api", "Shadowglass app API", CriticalityLevel.LOW),
            ("vault-gateway", "Credentials vault", CriticalityLevel.CRITICAL),
            ("x1200", "Swarm brain cloud", CriticalityLevel.HIGH),
        ]

        for svc_id, notes, crit in working_cloud_services:
            self.services[svc_id] = ServiceNode(
                service_id=svc_id,
                name=svc_id.replace("-", " ").title(),
                tier=ServiceTier.CLOUD_RUN,
                status=ServiceStatus.WORKING,
                url=f"https://{svc_id}-249995513427.us-central1.run.app",
                criticality=crit,
                has_health_check=True,
                notes=notes
            )

        # =========================================================
        # CLOUD RUN SERVICES - NOT DEPLOYED (CRITICAL)
        # =========================================================
        not_deployed_critical = [
            ("gs343", "Core error handling - 45,962 templates", 5003),
            ("gs343-healer", "Error healing system", 5004),
            ("phoenix", "Auto-healing system", 8046),
            ("gs343-gateway", "Cloud access to GS343", 5005),
        ]

        for svc_id, notes, port in not_deployed_critical:
            self.services[svc_id] = ServiceNode(
                service_id=svc_id,
                name=svc_id.replace("-", " ").title(),
                tier=ServiceTier.CLOUD_RUN,
                status=ServiceStatus.NOT_DEPLOYED,
                port=port,
                url=f"https://{svc_id}-249995513427.us-central1.run.app",
                criticality=CriticalityLevel.CRITICAL,
                has_health_check=False,
                notes=notes
            )

        # =========================================================
        # LOCAL SERVICES
        # =========================================================
        local_services = [
            ("chat-memory-api", 8385, ServiceStatus.WORKING, CriticalityLevel.HIGH, 10.0),
            ("gs343-local", 5003, ServiceStatus.NOT_RUNNING, CriticalityLevel.CRITICAL, 9.5),
            ("phoenix-local", 8046, ServiceStatus.NOT_RUNNING, CriticalityLevel.CRITICAL, 11.0),
            ("x1200-swarm-brain", 12000, ServiceStatus.WORKING, CriticalityLevel.HIGH, 10.5),
            ("omega-memory-gateway", 11181, ServiceStatus.NOT_RUNNING, CriticalityLevel.HIGH, None),
            ("crystal-search", 8048, ServiceStatus.NOT_RUNNING, CriticalityLevel.HIGH, None),
        ]

        for svc_id, port, status, crit, auth in local_services:
            self.services[svc_id] = ServiceNode(
                service_id=svc_id,
                name=svc_id.replace("-", " ").title(),
                tier=ServiceTier.LOCAL,
                status=status,
                port=port,
                host="localhost",
                criticality=crit,
                authority_level=auth,
                has_health_check=status == ServiceStatus.WORKING
            )

        # =========================================================
        # LAN SERVICES
        # =========================================================
        self.services["prometheus-prime"] = ServiceNode(
            service_id="prometheus-prime",
            name="PROMETHEUS PRIME",
            tier=ServiceTier.LAN,
            status=ServiceStatus.WORKING,
            port=8370,
            host="192.168.1.202",
            criticality=CriticalityLevel.CRITICAL,
            authority_level=11.0,
            has_health_check=True,
            notes="v6.1.0, uptime 3w 6d, 206 endpoints"
        )

        self.services["prometheus-backup"] = ServiceNode(
            service_id="prometheus-backup",
            name="PROMETHEUS Backup Service",
            tier=ServiceTier.LAN,
            status=ServiceStatus.UNKNOWN,
            port=8386,
            host="192.168.1.202",
            criticality=CriticalityLevel.HIGH,
            has_health_check=False
        )

        # =========================================================
        # CLOUD INFRASTRUCTURE
        # =========================================================
        self.services["omniscient-sync"] = ServiceNode(
            service_id="omniscient-sync",
            name="OMNISCIENT Sync",
            tier=ServiceTier.CLOUD_INFRA,
            status=ServiceStatus.WORKING,
            url="https://omniscient-sync.bmcii1976.workers.dev",
            criticality=CriticalityLevel.HIGH,
            has_health_check=True,
            notes="v3.6.0, 27 policies"
        )

        # =========================================================
        # MCP SERVICES
        # =========================================================
        self.services["mega-gateway-mcp"] = ServiceNode(
            service_id="mega-gateway-mcp",
            name="MEGA GATEWAY MCP",
            tier=ServiceTier.MCP,
            status=ServiceStatus.WORKING,
            criticality=CriticalityLevel.HIGH,
            notes="v12.0.0, 1,876 servers, 35,836 tools"
        )

        # =========================================================
        # DEPENDENCIES (Real topology)
        # =========================================================
        self._load_dependencies()

        logger.info(f"Loaded {len(self.services)} services, {len(self.dependencies)} dependencies")

    def _load_dependencies(self):
        """Load real dependency relationships."""

        # Critical dependency chains
        deps = [
            # Vault depends on PROMETHEUS for validation
            ("vault-gateway", "prometheus-prime", "VALIDATES_WITH", True),
            ("vault-gateway", "prometheus-backup", "BACKS_UP_TO", True),

            # GS343 dependencies (error handling)
            ("gs343-local", "chat-memory-api", "LOGS_TO", False),
            ("gs343-healer", "gs343-local", "REQUIRES", True),
            ("gs343-gateway", "gs343-local", "REQUIRES", True),

            # Phoenix depends on GS343 for error intelligence
            ("phoenix-local", "gs343-local", "REQUIRES", True),

            # X1200 swarm dependencies
            ("x1200-swarm-brain", "chat-memory-api", "STORES_IN", False),
            ("x1200", "x1200-swarm-brain", "CLOUD_FACADE_FOR", True),

            # Memory system chain
            ("crystal-memory", "omega-memory-gateway", "STORES_IN", True),
            ("chat-memory-api", "crystal-memory", "SYNCS_WITH", False),

            # Monitoring chain
            ("sentinel-omni", "prometheus-prime", "MONITORS", False),
            ("sentinel-omni", "gs343-local", "ALERTS_TO", True),

            # Auth chain
            ("citadel", "vault-gateway", "AUTHENTICATES_WITH", True),
            ("omnipresence-api", "citadel", "AUTHENTICATES_WITH", True),

            # OMNISCIENT sync dependencies
            ("omniscient-sync", "chat-memory-api", "SYNCS_FROM", False),

            # Forge build dependencies
            ("forge", "mega-gateway", "USES_TOOLS_FROM", False),
        ]

        for source, target, dep_type, is_critical in deps:
            # Only add if both services exist
            if source in self.services and target in self.services:
                self.dependencies.append(DependencyEdge(
                    source_id=source,
                    target_id=target,
                    dependency_type=dep_type,
                    is_critical=is_critical,
                    is_documented=True,
                    failover_exists=False  # Most don't have failovers
                ))

                # Update service nodes
                self.services[source].depends_on.append(target)
                self.services[target].depended_by.append(source)

    def get_topology_hash(self) -> str:
        """Deterministic hash of current topology state."""
        nodes = sorted(self.services.keys())
        edges = sorted([f"{d.source_id}->{d.target_id}" for d in self.dependencies])
        content = f"{nodes}{edges}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class PIECartographyAnalyzer:
    """
    PIE analysis of real system cartography.
    OBSERVER ONLY - No mutations.

    Answers:
    - Which dependency chains would fail silently?
    - Which systems violate replaceability doctrine?
    - Which components cannot be upgraded independently?
    - Which services have undocumented authority?
    """

    def __init__(self, cartography: SystemCartography):
        self.cartography = cartography
        self.analysis_id = f"PIE_CARTO_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"PIE Cartography Analyzer initialized: {self.analysis_id}")

    def analyze_silent_failure_chains(self) -> Dict:
        """
        QUERY: Which dependency chains would fail silently?

        Silent failures occur when:
        1. A critical dependency is NOT_RUNNING/NOT_DEPLOYED
        2. The dependent service has no health check for that dependency
        3. No alerting is configured for the failure
        """
        silent_failures = []

        for dep in self.cartography.dependencies:
            source = self.cartography.services.get(dep.source_id)
            target = self.cartography.services.get(dep.target_id)

            if not source or not target:
                continue

            # Check for silent failure conditions
            is_silent = False
            reasons = []

            # Target is down but no health check on dependency
            if target.status in [ServiceStatus.NOT_RUNNING, ServiceStatus.NOT_DEPLOYED]:
                if dep.is_critical:
                    is_silent = True
                    reasons.append(f"CRITICAL dependency {target.service_id} is {target.status.value}")

                    if not source.has_health_check:
                        reasons.append(f"Source {source.service_id} has no health check")

                    if not dep.failover_exists:
                        reasons.append("No failover configured")

            if is_silent:
                silent_failures.append({
                    "chain": f"{source.service_id} -> {target.service_id}",
                    "dependency_type": dep.dependency_type,
                    "target_status": target.status.value,
                    "source_criticality": source.criticality.value,
                    "reasons": reasons,
                    "impact": self._assess_cascade_impact(target.service_id)
                })

        return {
            "query": "Which dependency chains would fail silently?",
            "analysis_id": self.analysis_id,
            "silent_failure_count": len(silent_failures),
            "failures": silent_failures,
            "recommendation": "Deploy GS343 and Phoenix IMMEDIATELY - they are critical monitoring infrastructure"
        }

    def analyze_replaceability_violations(self) -> Dict:
        """
        QUERY: Which systems violate replaceability doctrine?

        Replaceability violations occur when:
        1. A service has no documented API contract
        2. A service has hard-coded dependencies
        3. A service cannot be swapped without affecting multiple dependents
        4. Single points of failure with no redundancy
        """
        violations = []

        for svc_id, svc in self.cartography.services.items():
            issues = []

            # Check for SPOF
            if len(svc.depended_by) >= 3 and svc.status != ServiceStatus.WORKING:
                issues.append({
                    "type": "SPOF_NOT_RUNNING",
                    "detail": f"{len(svc.depended_by)} services depend on this, but status is {svc.status.value}"
                })

            # Check for missing health checks on critical services
            if svc.criticality == CriticalityLevel.CRITICAL and not svc.has_health_check:
                issues.append({
                    "type": "CRITICAL_NO_HEALTHCHECK",
                    "detail": "Critical service without health monitoring"
                })

            # Check for undocumented authority
            if svc.authority_level and svc.authority_level >= 10.0 and not svc.documented:
                issues.append({
                    "type": "HIGH_AUTHORITY_UNDOCUMENTED",
                    "detail": f"Authority level {svc.authority_level} but undocumented"
                })

            # Check for tight coupling (many dependencies)
            if len(svc.depends_on) >= 4:
                issues.append({
                    "type": "TIGHT_COUPLING",
                    "detail": f"Depends on {len(svc.depends_on)} other services"
                })

            if issues:
                violations.append({
                    "service_id": svc_id,
                    "name": svc.name,
                    "criticality": svc.criticality.value,
                    "issues": issues
                })

        return {
            "query": "Which systems violate replaceability doctrine?",
            "analysis_id": self.analysis_id,
            "violation_count": len(violations),
            "violations": violations,
            "doctrine": "Every component should be replaceable without cascading failures"
        }

    def analyze_independent_upgrade_blockers(self) -> Dict:
        """
        QUERY: Which components cannot be upgraded independently?

        Upgrade blockers occur when:
        1. Circular dependencies exist
        2. Version coupling is undocumented
        3. Shared state without versioning
        4. No API versioning on critical interfaces
        """
        blockers = []

        # Find circular dependencies
        circular = self._find_circular_dependencies()
        for cycle in circular:
            blockers.append({
                "type": "CIRCULAR_DEPENDENCY",
                "components": cycle,
                "impact": "Cannot upgrade any component in cycle independently"
            })

        # Find tightly coupled clusters
        clusters = self._find_tight_clusters()
        for cluster in clusters:
            if len(cluster) >= 3:
                blockers.append({
                    "type": "TIGHT_CLUSTER",
                    "components": list(cluster),
                    "impact": "Must coordinate upgrades across cluster"
                })

        # Find services with undocumented dependencies
        for svc_id, svc in self.cartography.services.items():
            undoc_deps = []
            for dep in self.cartography.dependencies:
                if dep.source_id == svc_id and not dep.is_documented:
                    undoc_deps.append(dep.target_id)

            if undoc_deps:
                blockers.append({
                    "type": "UNDOCUMENTED_DEPENDENCIES",
                    "service": svc_id,
                    "undocumented_deps": undoc_deps,
                    "impact": "Upgrade may break unknown consumers"
                })

        return {
            "query": "Which components cannot be upgraded independently?",
            "analysis_id": self.analysis_id,
            "blocker_count": len(blockers),
            "blockers": blockers,
            "recommendation": "Document all dependencies before major upgrades"
        }

    def analyze_undocumented_authority(self) -> Dict:
        """
        QUERY: Which services have undocumented authority?

        Undocumented authority occurs when:
        1. Service makes decisions without clear ownership
        2. Authority level is not defined
        3. Override capabilities are unclear
        4. Escalation paths are missing
        """
        undocumented = []

        for svc_id, svc in self.cartography.services.items():
            issues = []

            # No authority level defined
            if svc.authority_level is None:
                issues.append("No authority level defined")

            # Critical service without clear ownership
            if svc.criticality in [CriticalityLevel.CRITICAL, CriticalityLevel.HIGH]:
                if not svc.notes:
                    issues.append("Critical service without documentation")

            # Services that others depend on but have no authority defined
            if len(svc.depended_by) >= 2 and svc.authority_level is None:
                issues.append(f"Authoritative to {len(svc.depended_by)} services but no authority level")

            # Services making decisions (healer, overseer) without clear scope
            if any(x in svc_id.lower() for x in ["healer", "overseer", "gateway", "citadel"]):
                if svc.authority_level is None:
                    issues.append("Decision-making service without authority classification")

            if issues:
                undocumented.append({
                    "service_id": svc_id,
                    "name": svc.name,
                    "tier": svc.tier.value,
                    "status": svc.status.value,
                    "depended_by_count": len(svc.depended_by),
                    "issues": issues
                })

        return {
            "query": "Which services have undocumented authority?",
            "analysis_id": self.analysis_id,
            "undocumented_count": len(undocumented),
            "services": undocumented,
            "recommendation": "Define authority levels for all services using TIER 100-20 framework"
        }

    def _assess_cascade_impact(self, service_id: str) -> str:
        """Assess cascade impact if service fails."""
        svc = self.cartography.services.get(service_id)
        if not svc:
            return "UNKNOWN"

        dependent_count = len(svc.depended_by)
        if dependent_count == 0:
            return "ISOLATED"
        elif dependent_count <= 2:
            return "LIMITED"
        elif dependent_count <= 5:
            return "MODERATE"
        else:
            return "SEVERE"

    def _find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependency chains."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            svc = self.cartography.services.get(node)
            if svc:
                for dep_id in svc.depends_on:
                    dfs(dep_id, path.copy())

            rec_stack.remove(node)

        for svc_id in self.cartography.services:
            if svc_id not in visited:
                dfs(svc_id, [])

        return cycles

    def _find_tight_clusters(self) -> List[Set[str]]:
        """Find tightly coupled service clusters."""
        clusters = []

        # Build adjacency for bidirectional connections
        bidirectional = {}
        for svc_id, svc in self.cartography.services.items():
            connected = set(svc.depends_on) | set(svc.depended_by)
            bidirectional[svc_id] = connected

        # Find connected components with high connectivity
        visited = set()

        def bfs(start: str) -> Set[str]:
            cluster = set()
            queue = [start]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                cluster.add(node)
                for neighbor in bidirectional.get(node, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            return cluster

        for svc_id in self.cartography.services:
            if svc_id not in visited:
                cluster = bfs(svc_id)
                if len(cluster) >= 2:
                    clusters.append(cluster)

        return clusters

    def generate_full_report(self) -> Dict:
        """Generate comprehensive PIE cartography analysis."""

        logger.info("Generating full PIE cartography analysis...")

        report = {
            "report_id": self.analysis_id,
            "generated_at": datetime.utcnow().isoformat(),
            "topology_hash": self.cartography.get_topology_hash(),
            "service_count": len(self.cartography.services),
            "dependency_count": len(self.cartography.dependencies),

            "analyses": {
                "silent_failure_chains": self.analyze_silent_failure_chains(),
                "replaceability_violations": self.analyze_replaceability_violations(),
                "independent_upgrade_blockers": self.analyze_independent_upgrade_blockers(),
                "undocumented_authority": self.analyze_undocumented_authority(),
            },

            "executive_summary": self._generate_executive_summary()
        }

        logger.info(f"Report generated: {self.analysis_id}")
        return report

    def _generate_executive_summary(self) -> Dict:
        """Generate executive summary of findings."""

        # Count critical issues
        critical_down = sum(
            1 for s in self.cartography.services.values()
            if s.criticality == CriticalityLevel.CRITICAL
            and s.status != ServiceStatus.WORKING
        )

        spofs = [
            s for s in self.cartography.services.values()
            if len(s.depended_by) >= 3
        ]

        return {
            "critical_services_down": critical_down,
            "single_points_of_failure": len(spofs),
            "spof_services": [s.service_id for s in spofs],
            "immediate_action_required": [
                "Deploy GS343 (error handling infrastructure)",
                "Deploy Phoenix (auto-healing infrastructure)",
                "Establish health checks for all CRITICAL services",
                "Document authority levels for decision-making services"
            ],
            "risk_assessment": "HIGH" if critical_down >= 2 else "MEDIUM" if critical_down >= 1 else "LOW"
        }


def run_pie_analysis():
    """Execute PIE cartography analysis."""

    print("\n" + "="*70)
    print("PIE CARTOGRAPHY ANALYSIS")
    print("System Class: ISOLATED_REASONING_ENGINE | Mode: OBSERVER")
    print("="*70 + "\n")

    # Load real topology
    cartography = SystemCartography()

    # Initialize analyzer
    analyzer = PIECartographyAnalyzer(cartography)

    # Generate full report
    report = analyzer.generate_full_report()

    # Output results
    print(f"Analysis ID: {report['report_id']}")
    print(f"Topology Hash: {report['topology_hash']}")
    print(f"Services: {report['service_count']} | Dependencies: {report['dependency_count']}")
    print()

    # Executive Summary
    summary = report['executive_summary']
    print("=" * 50)
    print("EXECUTIVE SUMMARY")
    print("=" * 50)
    print(f"Risk Assessment: {summary['risk_assessment']}")
    print(f"Critical Services Down: {summary['critical_services_down']}")
    print(f"Single Points of Failure: {summary['single_points_of_failure']}")
    print(f"SPOFs: {', '.join(summary['spof_services'])}")
    print()
    print("IMMEDIATE ACTIONS REQUIRED:")
    for action in summary['immediate_action_required']:
        print(f"  - {action}")
    print()

    # Query Results
    analyses = report['analyses']

    # 1. Silent Failure Chains
    sfc = analyses['silent_failure_chains']
    print("=" * 50)
    print(f"QUERY: {sfc['query']}")
    print("=" * 50)
    print(f"Silent Failure Chains Found: {sfc['silent_failure_count']}")
    for f in sfc['failures']:
        print(f"  CHAIN: {f['chain']}")
        print(f"    Type: {f['dependency_type']}")
        print(f"    Impact: {f['impact']}")
        for r in f['reasons']:
            print(f"    - {r}")
    print(f"RECOMMENDATION: {sfc['recommendation']}")
    print()

    # 2. Replaceability Violations
    rv = analyses['replaceability_violations']
    print("=" * 50)
    print(f"QUERY: {rv['query']}")
    print("=" * 50)
    print(f"Violations Found: {rv['violation_count']}")
    for v in rv['violations'][:5]:  # Top 5
        print(f"  SERVICE: {v['service_id']} ({v['criticality']})")
        for issue in v['issues']:
            print(f"    - {issue['type']}: {issue['detail']}")
    print()

    # 3. Independent Upgrade Blockers
    iub = analyses['independent_upgrade_blockers']
    print("=" * 50)
    print(f"QUERY: {iub['query']}")
    print("=" * 50)
    print(f"Blockers Found: {iub['blocker_count']}")
    for b in iub['blockers'][:5]:  # Top 5
        print(f"  TYPE: {b['type']}")
        if 'components' in b:
            print(f"    Components: {', '.join(b['components'])}")
        print(f"    Impact: {b['impact']}")
    print()

    # 4. Undocumented Authority
    ua = analyses['undocumented_authority']
    print("=" * 50)
    print(f"QUERY: {ua['query']}")
    print("=" * 50)
    print(f"Services with Undocumented Authority: {ua['undocumented_count']}")
    for s in ua['services'][:5]:  # Top 5
        print(f"  SERVICE: {s['service_id']} ({s['tier']}, {s['status']})")
        for issue in s['issues']:
            print(f"    - {issue}")
    print(f"RECOMMENDATION: {ua['recommendation']}")
    print()

    print("=" * 70)
    print("PIE ANALYSIS COMPLETE")
    print("=" * 70)

    return report


if __name__ == "__main__":
    run_pie_analysis()
