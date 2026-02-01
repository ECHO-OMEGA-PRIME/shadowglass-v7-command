"""
PROGRAMMING INTELLIGENCE ENGINE - Failure Mode Analyzer
THEORETICAL VS REAL-WORLD BEHAVIOR MAPPING

Consumes:
- Postmortems
- Outage reports
- CVE advisories
- Incident analyses

Maps:
- What docs say should happen
- What actually happened
- Why the discrepancy exists

This creates institutional memory of failure modes
that pure documentation cannot capture.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from pathlib import Path
import re
import hashlib
import json
from loguru import logger


class FailureCategory(str, Enum):
    """Categories of failure modes."""
    CASCADING = "CASCADING"              # Failure spreads through system
    SILENT = "SILENT"                    # Failure without obvious symptoms
    DATA_CORRUPTION = "DATA_CORRUPTION"  # Data integrity compromised
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"  # Memory, CPU, disk, connections
    RACE_CONDITION = "RACE_CONDITION"    # Timing-dependent failures
    CONFIGURATION = "CONFIGURATION"      # Misconfiguration failures
    DEPENDENCY = "DEPENDENCY"            # External dependency failures
    AUTHENTICATION = "AUTHENTICATION"    # Auth/authz failures
    NETWORK = "NETWORK"                  # Network-related failures
    SECURITY = "SECURITY"                # Security vulnerabilities
    DEPLOYMENT = "DEPLOYMENT"            # Deployment/rollout failures
    CAPACITY = "CAPACITY"                # Scaling/capacity failures


class ImpactLevel(str, Enum):
    """Impact level of a failure."""
    CATASTROPHIC = "CATASTROPHIC"  # Total system failure
    SEVERE = "SEVERE"              # Major functionality lost
    SIGNIFICANT = "SIGNIFICANT"    # Important features affected
    MODERATE = "MODERATE"          # Noticeable degradation
    MINOR = "MINOR"                # Minimal impact


@dataclass
class FailureEvidence:
    """Evidence from a failure incident."""
    source: str                    # Where this came from (postmortem, CVE, etc.)
    source_type: str               # POSTMORTEM, CVE, INCIDENT, OBSERVATION
    timestamp: datetime
    description: str
    raw_excerpt: Optional[str] = None
    confidence: float = 1.0


@dataclass
class BehaviorDiscrepancy:
    """
    Discrepancy between documented and actual behavior.
    The core unit of failure mode knowledge.
    """
    discrepancy_id: str
    component: str                 # What component/API/feature
    documented_behavior: str       # What docs say happens
    actual_behavior: str           # What actually happens
    trigger_conditions: List[str]  # When the discrepancy manifests
    impact: ImpactLevel
    evidence: List[FailureEvidence]
    mitigation: Optional[str] = None
    discovered_at: datetime = field(default_factory=datetime.now)

    @property
    def is_security_relevant(self) -> bool:
        """Check if this discrepancy has security implications."""
        security_keywords = [
            "authentication", "authorization", "permission", "privilege",
            "injection", "xss", "csrf", "bypass", "exposure", "leak"
        ]
        combined = f"{self.documented_behavior} {self.actual_behavior}".lower()
        return any(kw in combined for kw in security_keywords)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discrepancy_id": self.discrepancy_id,
            "component": self.component,
            "documented_behavior": self.documented_behavior,
            "actual_behavior": self.actual_behavior,
            "trigger_conditions": self.trigger_conditions,
            "impact": self.impact.value,
            "evidence_count": len(self.evidence),
            "is_security_relevant": self.is_security_relevant,
            "mitigation": self.mitigation,
            "discovered_at": self.discovered_at.isoformat()
        }


@dataclass
class FailureMode:
    """
    A documented failure mode with all associated knowledge.
    """
    mode_id: str
    category: FailureCategory
    name: str
    description: str
    affected_components: List[str]
    trigger_conditions: List[str]
    symptoms: List[str]
    impact: ImpactLevel
    root_causes: List[str]
    mitigations: List[str]
    detection_methods: List[str]
    evidence: List[FailureEvidence]
    related_discrepancies: List[str]  # discrepancy_ids
    discovered_at: datetime = field(default_factory=datetime.now)

    @property
    def risk_score(self) -> float:
        """Calculate risk score (0-10)."""
        impact_weights = {
            ImpactLevel.CATASTROPHIC: 10,
            ImpactLevel.SEVERE: 8,
            ImpactLevel.SIGNIFICANT: 6,
            ImpactLevel.MODERATE: 4,
            ImpactLevel.MINOR: 2
        }
        base = impact_weights.get(self.impact, 5)

        # Adjust for evidence confidence
        if self.evidence:
            avg_confidence = sum(e.confidence for e in self.evidence) / len(self.evidence)
            base *= avg_confidence

        return min(base, 10.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "affected_components": self.affected_components,
            "trigger_conditions": self.trigger_conditions,
            "symptoms": self.symptoms,
            "impact": self.impact.value,
            "root_causes": self.root_causes,
            "mitigations": self.mitigations,
            "detection_methods": self.detection_methods,
            "evidence_count": len(self.evidence),
            "risk_score": self.risk_score,
            "discovered_at": self.discovered_at.isoformat()
        }


@dataclass
class PostmortemAnalysis:
    """Analysis result from a postmortem document."""
    postmortem_id: str
    title: str
    incident_date: Optional[datetime]
    failure_modes: List[FailureMode]
    discrepancies: List[BehaviorDiscrepancy]
    lessons_learned: List[str]
    action_items: List[str]
    affected_systems: List[str]
    duration_minutes: Optional[int] = None
    analyzed_at: datetime = field(default_factory=datetime.now)


class FailureModeAnalyzer:
    """
    FAILURE MODE ANALYZER

    Consumes failure narratives (postmortems, CVEs, incident reports)
    and extracts institutional knowledge about:
    - How systems actually fail
    - Discrepancies between docs and reality
    - Conditions that trigger failures
    - Effective mitigations

    READ-ONLY: Does not modify source documents.
    """

    # Patterns for extracting failure information
    ROOT_CAUSE_PATTERNS = [
        r"root\s+cause[:\s]+([^\n]+)",
        r"caused\s+by[:\s]+([^\n]+)",
        r"the\s+issue\s+was[:\s]+([^\n]+)",
        r"failure\s+occurred\s+(?:because|when|due\s+to)[:\s]+([^\n]+)",
    ]

    IMPACT_PATTERNS = [
        r"impact[:\s]+([^\n]+)",
        r"affected[:\s]+([^\n]+)",
        r"resulted\s+in[:\s]+([^\n]+)",
        r"caused[:\s]+([^\n]+)",
    ]

    MITIGATION_PATTERNS = [
        r"mitigation[:\s]+([^\n]+)",
        r"fixed\s+by[:\s]+([^\n]+)",
        r"resolved\s+by[:\s]+([^\n]+)",
        r"workaround[:\s]+([^\n]+)",
        r"action\s+item[:\s]+([^\n]+)",
    ]

    SYMPTOM_PATTERNS = [
        r"symptoms?[:\s]+([^\n]+)",
        r"users?\s+(?:experienced|reported|saw)[:\s]+([^\n]+)",
        r"manifested\s+as[:\s]+([^\n]+)",
        r"error[:\s]+([^\n]+)",
    ]

    def __init__(self, persist_path: Optional[Path] = None):
        self.persist_path = persist_path
        self._failure_modes: Dict[str, FailureMode] = {}
        self._discrepancies: Dict[str, BehaviorDiscrepancy] = {}
        self._postmortems: Dict[str, PostmortemAnalysis] = {}

        if persist_path and persist_path.exists():
            self._load_from_disk()

        logger.info("Failure Mode Analyzer initialized")

    def analyze_postmortem(
        self,
        content: str,
        title: Optional[str] = None,
        incident_date: Optional[datetime] = None,
        source_id: Optional[str] = None
    ) -> PostmortemAnalysis:
        """
        Analyze a postmortem document and extract failure knowledge.
        """
        postmortem_id = source_id or f"pm_{hashlib.sha256(content.encode()).hexdigest()[:8]}"

        # Extract failure information
        root_causes = self._extract_patterns(content, self.ROOT_CAUSE_PATTERNS)
        impacts = self._extract_patterns(content, self.IMPACT_PATTERNS)
        mitigations = self._extract_patterns(content, self.MITIGATION_PATTERNS)
        symptoms = self._extract_patterns(content, self.SYMPTOM_PATTERNS)

        # Determine failure category
        category = self._classify_failure_category(content)

        # Determine impact level
        impact = self._assess_impact_level(content, impacts)

        # Extract affected systems
        affected = self._extract_affected_systems(content)

        # Build failure mode
        failure_mode = FailureMode(
            mode_id=f"fm_{postmortem_id}",
            category=category,
            name=title or self._extract_title(content),
            description=self._extract_summary(content),
            affected_components=affected,
            trigger_conditions=self._extract_triggers(content),
            symptoms=symptoms,
            impact=impact,
            root_causes=root_causes,
            mitigations=mitigations,
            detection_methods=self._extract_detection_methods(content),
            evidence=[FailureEvidence(
                source=postmortem_id,
                source_type="POSTMORTEM",
                timestamp=incident_date or datetime.now(),
                description="Extracted from postmortem analysis"
            )],
            related_discrepancies=[]
        )

        # Check for behavior discrepancies
        discrepancies = self._extract_discrepancies(content, postmortem_id)

        # Extract lessons learned
        lessons = self._extract_lessons(content)

        # Extract action items
        actions = self._extract_action_items(content)

        # Register failure mode
        self._failure_modes[failure_mode.mode_id] = failure_mode

        # Register discrepancies
        for disc in discrepancies:
            self._discrepancies[disc.discrepancy_id] = disc
            failure_mode.related_discrepancies.append(disc.discrepancy_id)

        analysis = PostmortemAnalysis(
            postmortem_id=postmortem_id,
            title=title or self._extract_title(content),
            incident_date=incident_date,
            failure_modes=[failure_mode],
            discrepancies=discrepancies,
            lessons_learned=lessons,
            action_items=actions,
            affected_systems=affected,
            duration_minutes=self._extract_duration(content)
        )

        self._postmortems[postmortem_id] = analysis

        if self.persist_path:
            self._persist_to_disk()

        logger.info(
            f"Postmortem analyzed: {postmortem_id} | "
            f"Failure modes: {len(analysis.failure_modes)} | "
            f"Discrepancies: {len(analysis.discrepancies)}"
        )

        return analysis

    def analyze_cve(
        self,
        cve_id: str,
        description: str,
        affected_products: List[str],
        severity: str,
        fix_version: Optional[str] = None
    ) -> FailureMode:
        """
        Analyze a CVE and create a failure mode entry.
        """
        # Map CVE severity to impact
        severity_map = {
            "critical": ImpactLevel.CATASTROPHIC,
            "high": ImpactLevel.SEVERE,
            "medium": ImpactLevel.SIGNIFICANT,
            "low": ImpactLevel.MODERATE,
        }
        impact = severity_map.get(severity.lower(), ImpactLevel.MODERATE)

        # Determine category from description
        category = self._classify_failure_category(description)
        if category == FailureCategory.CONFIGURATION:
            # CVEs are typically security
            category = FailureCategory.SECURITY

        failure_mode = FailureMode(
            mode_id=f"cve_{cve_id}",
            category=category,
            name=f"Security Vulnerability: {cve_id}",
            description=description,
            affected_components=affected_products,
            trigger_conditions=["Exploitation of vulnerability"],
            symptoms=["Security compromise"],
            impact=impact,
            root_causes=[description],
            mitigations=[f"Upgrade to {fix_version}" if fix_version else "Apply vendor patch"],
            detection_methods=["Vulnerability scanning", "Security audit"],
            evidence=[FailureEvidence(
                source=cve_id,
                source_type="CVE",
                timestamp=datetime.now(),
                description=description
            )],
            related_discrepancies=[]
        )

        self._failure_modes[failure_mode.mode_id] = failure_mode

        if self.persist_path:
            self._persist_to_disk()

        return failure_mode

    def register_discrepancy(
        self,
        component: str,
        documented_behavior: str,
        actual_behavior: str,
        trigger_conditions: List[str],
        evidence_source: str,
        impact: ImpactLevel = ImpactLevel.MODERATE
    ) -> BehaviorDiscrepancy:
        """
        Register a behavior discrepancy (docs say X, reality does Y).
        """
        disc_id = f"disc_{hashlib.sha256(f'{component}{documented_behavior}'.encode()).hexdigest()[:8]}"

        discrepancy = BehaviorDiscrepancy(
            discrepancy_id=disc_id,
            component=component,
            documented_behavior=documented_behavior,
            actual_behavior=actual_behavior,
            trigger_conditions=trigger_conditions,
            impact=impact,
            evidence=[FailureEvidence(
                source=evidence_source,
                source_type="OBSERVATION",
                timestamp=datetime.now(),
                description=f"Documented: {documented_behavior}. Actual: {actual_behavior}"
            )]
        )

        self._discrepancies[disc_id] = discrepancy

        if self.persist_path:
            self._persist_to_disk()

        logger.info(f"Discrepancy registered: {disc_id} for {component}")

        return discrepancy

    def _extract_patterns(self, content: str, patterns: List[str]) -> List[str]:
        """Extract information using regex patterns."""
        results = []
        content_lower = content.lower()

        for pattern in patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip().rstrip('.')
                if cleaned and len(cleaned) > 10 and cleaned not in results:
                    results.append(cleaned)

        return results[:10]  # Limit

    def _classify_failure_category(self, content: str) -> FailureCategory:
        """Classify the failure category from content."""
        content_lower = content.lower()

        category_keywords = {
            FailureCategory.CASCADING: ["cascade", "domino", "chain reaction", "propagat"],
            FailureCategory.SILENT: ["silent", "undetected", "invisible", "hidden failure"],
            FailureCategory.DATA_CORRUPTION: ["corrupt", "data loss", "inconsistent data"],
            FailureCategory.RESOURCE_EXHAUSTION: ["memory", "oom", "cpu", "disk full", "exhaust", "limit"],
            FailureCategory.RACE_CONDITION: ["race", "timing", "concurrent", "deadlock"],
            FailureCategory.CONFIGURATION: ["config", "misconfigur", "setting", "parameter"],
            FailureCategory.DEPENDENCY: ["dependency", "upstream", "downstream", "third party"],
            FailureCategory.AUTHENTICATION: ["auth", "login", "permission", "access denied"],
            FailureCategory.NETWORK: ["network", "timeout", "connection", "dns", "latency"],
            FailureCategory.SECURITY: ["security", "vulnerab", "exploit", "attack", "breach"],
            FailureCategory.DEPLOYMENT: ["deploy", "rollout", "release", "rollback"],
            FailureCategory.CAPACITY: ["capacity", "scale", "load", "traffic spike"],
        }

        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=scores.get)

        return FailureCategory.CONFIGURATION  # Default

    def _assess_impact_level(self, content: str, impacts: List[str]) -> ImpactLevel:
        """Assess impact level from content."""
        content_lower = content.lower()

        if any(kw in content_lower for kw in ["total outage", "complete failure", "catastrophic", "all users"]):
            return ImpactLevel.CATASTROPHIC
        if any(kw in content_lower for kw in ["major", "severe", "critical", "widespread"]):
            return ImpactLevel.SEVERE
        if any(kw in content_lower for kw in ["significant", "many users", "important"]):
            return ImpactLevel.SIGNIFICANT
        if any(kw in content_lower for kw in ["moderate", "some users", "partial"]):
            return ImpactLevel.MODERATE

        return ImpactLevel.MINOR

    def _extract_affected_systems(self, content: str) -> List[str]:
        """Extract affected systems from content."""
        # Look for common system patterns
        patterns = [
            r"([\w-]+)\s+(?:service|api|database|server|cluster)",
            r"affected:\s+([^\n]+)",
        ]

        systems = []
        for pattern in patterns:
            matches = re.findall(pattern, content.lower())
            systems.extend(matches)

        return list(set(systems))[:10]

    def _extract_triggers(self, content: str) -> List[str]:
        """Extract trigger conditions."""
        patterns = [
            r"triggered\s+(?:by|when)[:\s]+([^\n]+)",
            r"occurred\s+when[:\s]+([^\n]+)",
            r"happens?\s+when[:\s]+([^\n]+)",
        ]
        return self._extract_patterns(content, patterns)

    def _extract_detection_methods(self, content: str) -> List[str]:
        """Extract detection methods."""
        patterns = [
            r"detected\s+(?:by|via|through)[:\s]+([^\n]+)",
            r"alert(?:ed|s?)[:\s]+([^\n]+)",
            r"monitoring\s+showed[:\s]+([^\n]+)",
        ]
        return self._extract_patterns(content, patterns)

    def _extract_title(self, content: str) -> str:
        """Extract a title from content."""
        lines = content.strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 100 and not line.startswith('#'):
                return line
        return "Untitled Incident"

    def _extract_summary(self, content: str) -> str:
        """Extract a summary."""
        # Look for summary section
        match = re.search(r"(?:summary|overview|tldr)[:\s]+([^\n]+(?:\n[^\n]+)?)", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:500]

        # First paragraph
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50:
                return para[:500]

        return content[:500]

    def _extract_discrepancies(
        self,
        content: str,
        source_id: str
    ) -> List[BehaviorDiscrepancy]:
        """Extract behavior discrepancies from content."""
        discrepancies = []

        # Patterns for "expected X but got Y"
        patterns = [
            r"expected\s+([^,]+),?\s+but\s+(?:got|received|saw)\s+([^\n]+)",
            r"should\s+(?:have\s+)?([^,]+),?\s+but\s+(?:instead|actually)\s+([^\n]+)",
            r"documentation\s+(?:says|states)\s+([^,]+),?\s+but\s+([^\n]+)",
            r"supposed\s+to\s+([^,]+),?\s+(?:but|however)\s+([^\n]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for expected, actual in matches:
                disc = BehaviorDiscrepancy(
                    discrepancy_id=f"disc_{source_id}_{len(discrepancies)}",
                    component="unknown",
                    documented_behavior=expected.strip(),
                    actual_behavior=actual.strip(),
                    trigger_conditions=["See postmortem"],
                    impact=ImpactLevel.MODERATE,
                    evidence=[FailureEvidence(
                        source=source_id,
                        source_type="POSTMORTEM",
                        timestamp=datetime.now(),
                        description=f"Expected: {expected}. Actual: {actual}"
                    )]
                )
                discrepancies.append(disc)

        return discrepancies

    def _extract_lessons(self, content: str) -> List[str]:
        """Extract lessons learned."""
        patterns = [
            r"lesson[s]?\s+learned[:\s]+([^\n]+)",
            r"takeaway[s]?[:\s]+([^\n]+)",
            r"we\s+learned[:\s]+([^\n]+)",
            r"in\s+the\s+future[,\s]+([^\n]+)",
        ]
        return self._extract_patterns(content, patterns)

    def _extract_action_items(self, content: str) -> List[str]:
        """Extract action items."""
        patterns = [
            r"action\s+item[s]?[:\s]+([^\n]+)",
            r"todo[:\s]+([^\n]+)",
            r"follow[- ]up[:\s]+([^\n]+)",
            r"we\s+(?:will|should|must)[:\s]+([^\n]+)",
        ]
        return self._extract_patterns(content, patterns)

    def _extract_duration(self, content: str) -> Optional[int]:
        """Extract incident duration in minutes."""
        patterns = [
            r"duration[:\s]+(\d+)\s*(?:minute|min)",
            r"lasted\s+(\d+)\s*(?:minute|min)",
            r"(\d+)\s*(?:minute|min)[s]?\s+(?:outage|downtime)",
            r"duration[:\s]+(\d+)\s*hour",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                duration = int(match.group(1))
                if "hour" in pattern:
                    duration *= 60
                return duration

        return None

    def get_failure_modes(
        self,
        category: Optional[FailureCategory] = None,
        min_risk_score: float = 0.0
    ) -> List[FailureMode]:
        """Get failure modes with optional filtering."""
        modes = list(self._failure_modes.values())

        if category:
            modes = [m for m in modes if m.category == category]

        modes = [m for m in modes if m.risk_score >= min_risk_score]

        return sorted(modes, key=lambda m: m.risk_score, reverse=True)

    def get_discrepancies(
        self,
        component: Optional[str] = None,
        security_only: bool = False
    ) -> List[BehaviorDiscrepancy]:
        """Get behavior discrepancies with optional filtering."""
        discs = list(self._discrepancies.values())

        if component:
            discs = [d for d in discs if component.lower() in d.component.lower()]

        if security_only:
            discs = [d for d in discs if d.is_security_relevant]

        return discs

    def query_for_component(self, component: str) -> Dict[str, Any]:
        """
        Query all failure knowledge for a specific component.
        Returns failure modes and discrepancies affecting this component.
        """
        relevant_modes = []
        relevant_discs = []

        component_lower = component.lower()

        for mode in self._failure_modes.values():
            if any(component_lower in c.lower() for c in mode.affected_components):
                relevant_modes.append(mode)

        for disc in self._discrepancies.values():
            if component_lower in disc.component.lower():
                relevant_discs.append(disc)

        return {
            "component": component,
            "failure_modes": [m.to_dict() for m in relevant_modes],
            "behavior_discrepancies": [d.to_dict() for d in relevant_discs],
            "risk_summary": {
                "total_failure_modes": len(relevant_modes),
                "total_discrepancies": len(relevant_discs),
                "max_risk_score": max([m.risk_score for m in relevant_modes], default=0),
                "security_concerns": len([d for d in relevant_discs if d.is_security_relevant])
            }
        }

    def generate_report(self) -> Dict[str, Any]:
        """Generate complete failure mode report."""
        all_modes = list(self._failure_modes.values())
        all_discs = list(self._discrepancies.values())

        return {
            "report_id": f"failure_report_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_failure_modes": len(all_modes),
                "total_discrepancies": len(all_discs),
                "total_postmortems": len(self._postmortems),
                "by_category": {
                    cat.value: len([m for m in all_modes if m.category == cat])
                    for cat in FailureCategory
                },
                "by_impact": {
                    level.value: len([m for m in all_modes if m.impact == level])
                    for level in ImpactLevel
                },
                "security_discrepancies": len([d for d in all_discs if d.is_security_relevant])
            },
            "high_risk_modes": [
                m.to_dict() for m in sorted(all_modes, key=lambda x: x.risk_score, reverse=True)[:10]
            ],
            "critical_discrepancies": [
                d.to_dict() for d in all_discs if d.impact in {ImpactLevel.CATASTROPHIC, ImpactLevel.SEVERE}
            ]
        }

    def _persist_to_disk(self):
        """Persist to disk."""
        if not self.persist_path:
            return

        data = {
            "failure_modes": {k: v.to_dict() for k, v in self._failure_modes.items()},
            "discrepancies": {k: v.to_dict() for k, v in self._discrepancies.items()},
            "persisted_at": datetime.now().isoformat()
        }

        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_from_disk(self):
        """Load from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        # Load implementation would go here
        logger.info("Loaded failure mode data from disk")


# Self-test
def _self_test():
    """Validate failure mode analyzer."""
    analyzer = FailureModeAnalyzer()

    # Test postmortem analysis
    postmortem = """
    # Database Outage - January 15, 2024

    ## Summary
    The main database cluster experienced a cascading failure affecting all users.

    ## Root Cause
    Root cause: A misconfigured connection pool caused connection exhaustion.

    ## Impact
    Impact: Complete outage for 45 minutes affecting all production services.

    ## Timeline
    Duration: 45 minutes

    ## Mitigation
    Mitigation: Increased connection pool limits and added monitoring.

    ## Lessons Learned
    Lesson learned: We should have had better capacity planning.

    ## Action Items
    Action item: Implement connection pool monitoring dashboards.
    """

    analysis = analyzer.analyze_postmortem(postmortem, title="Database Outage")

    assert len(analysis.failure_modes) > 0, "Should extract failure modes"
    assert analysis.failure_modes[0].category in FailureCategory, "Should classify category"
    assert len(analysis.lessons_learned) > 0, "Should extract lessons"

    # Test discrepancy registration
    disc = analyzer.register_discrepancy(
        component="API Gateway",
        documented_behavior="Timeout after 30 seconds",
        actual_behavior="Hangs indefinitely under load",
        trigger_conditions=["High traffic", "Backend slow"],
        evidence_source="production_observation"
    )

    assert disc is not None, "Should create discrepancy"

    # Test query
    query_result = analyzer.query_for_component("database")
    assert "failure_modes" in query_result, "Should return failure modes"

    logger.info("Failure Mode Analyzer self-test PASSED")


if __name__ == "__main__":
    _self_test()
