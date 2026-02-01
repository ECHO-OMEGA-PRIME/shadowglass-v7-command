"""
PROGRAMMING INTELLIGENCE ENGINE - Drift Sentinel (READ-ONLY)
DOCUMENTATION DRIFT OBSERVATION

CRITICAL CHANGE FROM ORIGINAL:
This is the READ-ONLY variant. It:
- Detects drift
- Logs warnings
- Emits alerts

It does NOT:
- Auto-remediate
- Modify doctrines
- Archive versions
- Broadcast mutations

Observation only. Never interference.
The original drift_sentinel.py remains for full functionality.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
State: ENGINEERING_OBSERVER
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from enum import Enum
import hashlib
import json
from loguru import logger

from ..engine.models import (
    EngineeringDoctrine,
    VersionMetadata,
    VersionStatus,
    DriftType,
    DriftAlert
)


class DriftSeverity(str, Enum):
    """Severity classification for drift alerts."""
    CRITICAL = "CRITICAL"    # Immediate attention required
    HIGH = "HIGH"            # Should address soon
    MEDIUM = "MEDIUM"        # Plan to address
    LOW = "LOW"              # Informational
    INFO = "INFO"            # Logged for audit


@dataclass
class DriftObservation:
    """
    READ-ONLY observation of drift.
    Does not trigger remediation - observation only.
    """
    observation_id: str
    doctrine_id: str
    drift_type: DriftType
    severity: DriftSeverity
    observed_at: datetime
    description: str
    old_state: Dict[str, Any]
    new_state: Dict[str, Any]
    evidence: List[str]
    recommended_action: str

    # Observer state markers
    auto_remediation_blocked: bool = True
    requires_human_review: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "doctrine_id": self.doctrine_id,
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "observed_at": self.observed_at.isoformat(),
            "description": self.description,
            "old_state": self.old_state,
            "new_state": self.new_state,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
            "observer_state": {
                "auto_remediation_blocked": self.auto_remediation_blocked,
                "requires_human_review": self.requires_human_review
            }
        }


@dataclass
class ContentSnapshot:
    """Snapshot of content for drift comparison."""
    snapshot_id: str
    source_id: str
    content_hash: str
    captured_at: datetime
    metadata: Dict[str, Any]


class DriftSentinelReadOnly:
    """
    DRIFT SENTINEL - READ-ONLY OBSERVER

    Detects documentation drift without modifying anything.
    All observations are logged but no remediation is performed.

    This is the OBSERVER variant for engineering analysis.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or Path(__file__).parent.parent / "logs" / "drift_observations.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory state (read-only observations)
        self._observations: List[DriftObservation] = []
        self._snapshots: Dict[str, ContentSnapshot] = {}
        self._content_hashes: Dict[str, str] = {}

        logger.info("Drift Sentinel (READ-ONLY) initialized")
        logger.info("AUTO-REMEDIATION: DISABLED | OBSERVER MODE: ACTIVE")

    def observe_doctrine(
        self,
        doctrine: EngineeringDoctrine,
        current_source_content: Optional[str] = None
    ) -> List[DriftObservation]:
        """
        Observe a doctrine for potential drift.
        READ-ONLY - does not modify the doctrine.

        Returns list of drift observations (may be empty).
        """
        observations = []

        # Check version metadata drift
        if doctrine.version_metadata:
            version_obs = self._check_version_drift(doctrine)
            observations.extend(version_obs)

        # Check content drift if source provided
        if current_source_content:
            content_obs = self._check_content_drift(doctrine, current_source_content)
            observations.extend(content_obs)

        # Check source reference staleness
        source_obs = self._check_source_staleness(doctrine)
        observations.extend(source_obs)

        # Log all observations
        for obs in observations:
            self._log_observation(obs)
            self._observations.append(obs)

        return observations

    def _check_version_drift(
        self,
        doctrine: EngineeringDoctrine
    ) -> List[DriftObservation]:
        """Check for version-related drift."""
        observations = []
        meta = doctrine.version_metadata

        if not meta:
            return observations

        today = date.today()

        # Check for deprecation that should have happened
        if meta.status == VersionStatus.ACTIVE and meta.version_deprecated:
            observations.append(DriftObservation(
                observation_id=f"drift_{doctrine.doctrine_id}_dep_{datetime.now().timestamp()}",
                doctrine_id=doctrine.doctrine_id,
                drift_type=DriftType.DEPRECATION,
                severity=DriftSeverity.HIGH,
                observed_at=datetime.now(),
                description=f"Doctrine marked ACTIVE but has deprecation version {meta.version_deprecated}",
                old_state={"status": "ACTIVE"},
                new_state={"status": "should be DEPRECATED"},
                evidence=[f"version_deprecated: {meta.version_deprecated}"],
                recommended_action=f"Update status to DEPRECATED. Consider migration to: {meta.replacement_path or 'TBD'}"
            ))

        # Check for removal that should have happened
        if meta.status != VersionStatus.REMOVED and meta.version_removed:
            observations.append(DriftObservation(
                observation_id=f"drift_{doctrine.doctrine_id}_rem_{datetime.now().timestamp()}",
                doctrine_id=doctrine.doctrine_id,
                drift_type=DriftType.API_REMOVAL,
                severity=DriftSeverity.CRITICAL,
                observed_at=datetime.now(),
                description=f"Doctrine has removal version {meta.version_removed} but status is {meta.status.value}",
                old_state={"status": meta.status.value},
                new_state={"status": "should be REMOVED"},
                evidence=[f"version_removed: {meta.version_removed}"],
                recommended_action=f"Verify if removed. If so, update status and remove from active use."
            ))

        # Check for stale verification
        if meta.last_verified:
            days_since = (datetime.now() - meta.last_verified).days
            if days_since > 90:
                severity = DriftSeverity.HIGH if days_since > 180 else DriftSeverity.MEDIUM
                observations.append(DriftObservation(
                    observation_id=f"drift_{doctrine.doctrine_id}_stale_{datetime.now().timestamp()}",
                    doctrine_id=doctrine.doctrine_id,
                    drift_type=DriftType.BEHAVIOR_CHANGE,
                    severity=severity,
                    observed_at=datetime.now(),
                    description=f"Doctrine not verified in {days_since} days",
                    old_state={"last_verified": meta.last_verified.isoformat()},
                    new_state={"days_stale": days_since},
                    evidence=[f"Last verified: {meta.last_verified.isoformat()}"],
                    recommended_action="Re-verify against current source documentation"
                ))

        return observations

    def _check_content_drift(
        self,
        doctrine: EngineeringDoctrine,
        current_content: str
    ) -> List[DriftObservation]:
        """Check for content drift by comparing hashes."""
        observations = []

        current_hash = hashlib.sha256(current_content.encode()).hexdigest()[:16]

        # Get stored hash for comparison
        stored_hash = self._content_hashes.get(doctrine.doctrine_id)

        if stored_hash and stored_hash != current_hash:
            # Content has changed
            observations.append(DriftObservation(
                observation_id=f"drift_{doctrine.doctrine_id}_content_{datetime.now().timestamp()}",
                doctrine_id=doctrine.doctrine_id,
                drift_type=DriftType.BEHAVIOR_CHANGE,
                severity=DriftSeverity.MEDIUM,
                observed_at=datetime.now(),
                description="Source content has changed since last snapshot",
                old_state={"content_hash": stored_hash},
                new_state={"content_hash": current_hash},
                evidence=["Content hash mismatch detected"],
                recommended_action="Review source changes and update doctrine if necessary"
            ))

        # Store current hash for future comparison (observation, not mutation)
        self._content_hashes[doctrine.doctrine_id] = current_hash

        return observations

    def _check_source_staleness(
        self,
        doctrine: EngineeringDoctrine
    ) -> List[DriftObservation]:
        """Check if source references are stale."""
        observations = []

        for source in doctrine.source_references:
            if source.last_accessed:
                days_since = (datetime.now() - source.last_accessed).days
                if days_since > 60:
                    observations.append(DriftObservation(
                        observation_id=f"drift_{doctrine.doctrine_id}_src_{source.source_id}_{datetime.now().timestamp()}",
                        doctrine_id=doctrine.doctrine_id,
                        drift_type=DriftType.BEHAVIOR_CHANGE,
                        severity=DriftSeverity.LOW,
                        observed_at=datetime.now(),
                        description=f"Source {source.source_id} not accessed in {days_since} days",
                        old_state={"last_accessed": source.last_accessed.isoformat()},
                        new_state={"days_stale": days_since},
                        evidence=[f"Source: {source.source_id}", f"URL: {source.url or 'N/A'}"],
                        recommended_action="Re-fetch source and verify content hasn't changed"
                    ))

        return observations

    def capture_snapshot(
        self,
        source_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> ContentSnapshot:
        """
        Capture a content snapshot for future comparison.
        This is still READ-ONLY - it doesn't modify the source.
        """
        snapshot = ContentSnapshot(
            snapshot_id=f"snap_{source_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            source_id=source_id,
            content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
            captured_at=datetime.now(),
            metadata=metadata or {}
        )

        self._snapshots[source_id] = snapshot
        self._content_hashes[source_id] = snapshot.content_hash

        return snapshot

    def compare_to_snapshot(
        self,
        source_id: str,
        current_content: str
    ) -> Optional[DriftObservation]:
        """
        Compare current content to stored snapshot.
        Returns observation if drift detected, None otherwise.
        """
        if source_id not in self._snapshots:
            return None

        snapshot = self._snapshots[source_id]
        current_hash = hashlib.sha256(current_content.encode()).hexdigest()[:16]

        if current_hash != snapshot.content_hash:
            return DriftObservation(
                observation_id=f"drift_snap_{source_id}_{datetime.now().timestamp()}",
                doctrine_id=source_id,
                drift_type=DriftType.BEHAVIOR_CHANGE,
                severity=DriftSeverity.MEDIUM,
                observed_at=datetime.now(),
                description=f"Content drift detected for {source_id}",
                old_state={
                    "snapshot_id": snapshot.snapshot_id,
                    "content_hash": snapshot.content_hash,
                    "captured_at": snapshot.captured_at.isoformat()
                },
                new_state={"content_hash": current_hash},
                evidence=["Hash mismatch between snapshot and current content"],
                recommended_action="Review changes and update affected doctrines"
            )

        return None

    def _log_observation(self, observation: DriftObservation):
        """Log observation to file (append-only)."""
        try:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(observation.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to log observation: {e}")

    def get_observations(
        self,
        doctrine_id: Optional[str] = None,
        severity: Optional[DriftSeverity] = None,
        drift_type: Optional[DriftType] = None,
        since: Optional[datetime] = None
    ) -> List[DriftObservation]:
        """Get observations with optional filtering."""
        result = self._observations

        if doctrine_id:
            result = [o for o in result if o.doctrine_id == doctrine_id]

        if severity:
            result = [o for o in result if o.severity == severity]

        if drift_type:
            result = [o for o in result if o.drift_type == drift_type]

        if since:
            result = [o for o in result if o.observed_at >= since]

        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all observations."""
        by_severity = {}
        by_type = {}

        for obs in self._observations:
            by_severity[obs.severity.value] = by_severity.get(obs.severity.value, 0) + 1
            by_type[obs.drift_type.value] = by_type.get(obs.drift_type.value, 0) + 1

        return {
            "total_observations": len(self._observations),
            "by_severity": by_severity,
            "by_type": by_type,
            "snapshots_stored": len(self._snapshots),
            "observer_mode": True,
            "auto_remediation": "DISABLED",
            "mutations": "BLOCKED"
        }

    def generate_observation_report(self) -> Dict[str, Any]:
        """
        Generate a complete observation report.
        READ-ONLY - summarizes without acting.
        """
        critical = [o for o in self._observations if o.severity == DriftSeverity.CRITICAL]
        high = [o for o in self._observations if o.severity == DriftSeverity.HIGH]

        report = {
            "report_id": f"drift_report_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "mode": "ENGINEERING_OBSERVER",
            "mutation_status": "DISABLED",
            "summary": self.get_summary(),
            "action_required": len(critical) + len(high),
            "critical_observations": [o.to_dict() for o in critical],
            "high_observations": [o.to_dict() for o in high[:10]],
            "recommendations": []
        }

        if critical:
            report["recommendations"].append(
                f"IMMEDIATE: {len(critical)} critical drift observations require review"
            )
        if high:
            report["recommendations"].append(
                f"PRIORITY: {len(high)} high severity drifts should be addressed"
            )

        return report


# Self-test
def _self_test():
    """Validate read-only drift sentinel."""
    from ..engine.models import SourceReference, AuthorityTier, TrustLevel

    sentinel = DriftSentinelReadOnly()

    # Create test doctrine
    meta = VersionMetadata(
        version_introduced="1.0.0",
        version_deprecated="2.0.0",
        status=VersionStatus.ACTIVE,  # Intentional mismatch
        last_verified=datetime(2024, 1, 1)
    )

    doctrine = EngineeringDoctrine(
        doctrine_id="test_doctrine",
        title="Test Doctrine",
        content="Test content",
        category="TEST",
        version_metadata=meta,
        source_references=[
            SourceReference(
                source_id="test_source",
                source_type="VENDOR_DOCS",
                authority_tier=AuthorityTier.PRIMARY_SOURCE,
                trust_level=TrustLevel.HIGH,
                last_accessed=datetime(2024, 1, 1)
            )
        ]
    )

    # Observe
    observations = sentinel.observe_doctrine(doctrine)

    # Should detect deprecation mismatch
    assert len(observations) > 0, "Should detect drift"
    assert any(o.drift_type == DriftType.DEPRECATION for o in observations), "Should detect deprecation drift"
    assert all(o.auto_remediation_blocked for o in observations), "Auto-remediation should be blocked"

    # Verify summary
    summary = sentinel.get_summary()
    assert summary["observer_mode"] is True, "Should be in observer mode"
    assert summary["auto_remediation"] == "DISABLED", "Auto-remediation should be disabled"

    logger.info("Drift Sentinel (READ-ONLY) self-test PASSED")


if __name__ == "__main__":
    _self_test()
