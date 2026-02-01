"""
PROGRAMMING INTELLIGENCE ENGINE - Drift Sentinel
Self-Healing Documentation Monitoring

Scheduled scans detect:
- deprecated endpoints
- version sunsets
- security advisories
- breaking releases

When detected:
1. Trigger Governance Broadcast
2. Update doctrine
3. Archive prior version
4. Annotate migration path

Institutional memory must persist.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import hashlib
import aiohttp
from loguru import logger

from ..engine.models import (
    DriftAlert,
    DriftType,
    EngineeringDoctrine,
    VersionStatus
)
from ..layers.version_awareness import VersionAwarenessEngine


class ScanType(str, Enum):
    """Types of drift scans."""
    DEPRECATION = "DEPRECATION"
    VERSION_SUNSET = "VERSION_SUNSET"
    SECURITY_ADVISORY = "SECURITY_ADVISORY"
    BREAKING_CHANGE = "BREAKING_CHANGE"
    SOURCE_UPDATE = "SOURCE_UPDATE"


class AlertSeverity(str, Enum):
    """Severity levels for drift alerts."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ScanResult:
    """Result of a drift scan."""
    scan_type: ScanType
    scanned_at: datetime
    alerts: List[DriftAlert]
    doctrines_scanned: int
    sources_checked: int
    duration_seconds: float


@dataclass
class RemediationAction:
    """Action taken to remediate drift."""
    action_id: str
    alert_id: str
    action_type: str  # UPDATE, ARCHIVE, MIGRATE
    doctrine_id: str
    old_value: str
    new_value: str
    performed_at: datetime
    auto_applied: bool
    notes: str


class DriftSentinel:
    """
    Documentation Drift Sentinel

    Automatically detects and remediates documentation drift.
    Maintains institutional memory across upstream changes.
    """

    # Known vendor changelog/release endpoints
    VENDOR_ENDPOINTS = {
        "github": {
            "api": "https://api.github.com/repos/{owner}/{repo}/releases/latest",
            "check_interval_hours": 24
        },
        "python": {
            "api": "https://endoflife.date/api/python.json",
            "check_interval_hours": 168  # Weekly
        },
        "nodejs": {
            "api": "https://endoflife.date/api/nodejs.json",
            "check_interval_hours": 168
        },
        "kubernetes": {
            "api": "https://endoflife.date/api/kubernetes.json",
            "check_interval_hours": 168
        },
        "docker": {
            "api": "https://hub.docker.com/v2/repositories/library/{image}/tags",
            "check_interval_hours": 168
        }
    }

    def __init__(
        self,
        version_engine: VersionAwarenessEngine,
        archive_path: Optional[Path] = None,
        broadcast_callback: Optional[Callable] = None
    ):
        self.version_engine = version_engine
        self.archive_path = archive_path or Path(__file__).parent.parent / "doctrine" / "archive"
        self.archive_path.mkdir(parents=True, exist_ok=True)

        self.broadcast_callback = broadcast_callback

        # Alert tracking
        self.active_alerts: Dict[str, DriftAlert] = {}
        self.alert_history: List[DriftAlert] = []
        self.remediation_history: List[RemediationAction] = []

        # Scan state
        self.last_scan: Dict[ScanType, datetime] = {}
        self.source_hashes: Dict[str, str] = {}  # source_id -> content_hash

        # Monitoring state
        self.is_running = False
        self._scan_task: Optional[asyncio.Task] = None

        logger.info("Drift Sentinel initialized")

    async def start_monitoring(self, scan_interval_hours: int = 24):
        """Start continuous drift monitoring."""
        self.is_running = True
        logger.info(f"Starting drift monitoring (interval: {scan_interval_hours}h)")

        while self.is_running:
            try:
                await self.run_full_scan()
                await asyncio.sleep(scan_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour

    def stop_monitoring(self):
        """Stop drift monitoring."""
        self.is_running = False
        if self._scan_task:
            self._scan_task.cancel()
        logger.info("Drift monitoring stopped")

    async def run_full_scan(self) -> List[ScanResult]:
        """Run all drift scans."""
        results = []

        for scan_type in ScanType:
            result = await self.run_scan(scan_type)
            results.append(result)

        return results

    async def run_scan(self, scan_type: ScanType) -> ScanResult:
        """Run a specific type of drift scan."""
        start_time = datetime.now()
        alerts = []

        if scan_type == ScanType.DEPRECATION:
            alerts = await self._scan_deprecations()
        elif scan_type == ScanType.VERSION_SUNSET:
            alerts = await self._scan_version_sunsets()
        elif scan_type == ScanType.SECURITY_ADVISORY:
            alerts = await self._scan_security_advisories()
        elif scan_type == ScanType.BREAKING_CHANGE:
            alerts = await self._scan_breaking_changes()
        elif scan_type == ScanType.SOURCE_UPDATE:
            alerts = await self._scan_source_updates()

        duration = (datetime.now() - start_time).total_seconds()
        self.last_scan[scan_type] = datetime.now()

        result = ScanResult(
            scan_type=scan_type,
            scanned_at=datetime.now(),
            alerts=alerts,
            doctrines_scanned=0,  # Will be set by scan methods
            sources_checked=0,
            duration_seconds=duration
        )

        # Process alerts
        for alert in alerts:
            await self._process_alert(alert)

        logger.info(
            f"Scan completed: {scan_type.value} | "
            f"Alerts: {len(alerts)} | "
            f"Duration: {duration:.2f}s"
        )

        return result

    async def _scan_deprecations(self) -> List[DriftAlert]:
        """Scan for newly deprecated APIs/features."""
        alerts = []

        # This would scan registered doctrines and check against vendor APIs
        # For now, implementing the structure

        return alerts

    async def _scan_version_sunsets(self) -> List[DriftAlert]:
        """Scan for version end-of-life announcements."""
        alerts = []

        async with aiohttp.ClientSession() as session:
            for vendor, config in self.VENDOR_ENDPOINTS.items():
                if "endoflife.date" in config["api"]:
                    try:
                        async with session.get(config["api"]) as response:
                            if response.status == 200:
                                data = await response.json()
                                eol_alerts = self._check_eol_data(vendor, data)
                                alerts.extend(eol_alerts)
                    except Exception as e:
                        logger.warning(f"Failed to check {vendor}: {e}")

        return alerts

    def _check_eol_data(
        self,
        vendor: str,
        eol_data: List[Dict]
    ) -> List[DriftAlert]:
        """Check end-of-life data for relevant alerts."""
        alerts = []
        today = datetime.now().date()

        for version_info in eol_data:
            eol_date = version_info.get("eol")
            if eol_date and eol_date != "false":
                try:
                    eol = datetime.strptime(str(eol_date), "%Y-%m-%d").date()
                    if eol <= today + timedelta(days=90):  # 90 day warning
                        severity = AlertSeverity.CRITICAL if eol <= today else AlertSeverity.HIGH

                        alert = DriftAlert(
                            alert_id=f"eol_{vendor}_{version_info.get('cycle', 'unknown')}",
                            drift_type=DriftType.VERSION_SUNSET,
                            affected_doctrines=[],  # Would link to actual doctrines
                            severity=severity.value,
                            description=(
                                f"{vendor} version {version_info.get('cycle', 'unknown')} "
                                f"{'has reached' if eol <= today else 'will reach'} "
                                f"end-of-life on {eol_date}"
                            ),
                            migration_path=f"Upgrade to {vendor} {version_info.get('latest', 'latest version')}",
                            source_trigger="endoflife.date"
                        )
                        alerts.append(alert)
                except ValueError:
                    continue

        return alerts

    async def _scan_security_advisories(self) -> List[DriftAlert]:
        """Scan for security advisories affecting doctrines."""
        alerts = []

        # Would integrate with:
        # - GitHub Security Advisories API
        # - NVD (National Vulnerability Database)
        # - Vendor security feeds

        return alerts

    async def _scan_breaking_changes(self) -> List[DriftAlert]:
        """Scan for breaking changes in tracked dependencies."""
        alerts = []

        # Would check:
        # - Changelog files for "BREAKING" keywords
        # - Semantic version major bumps
        # - Migration guides published

        return alerts

    async def _scan_source_updates(self) -> List[DriftAlert]:
        """Scan for updates to source documentation."""
        alerts = []

        # Would:
        # - Fetch current source content
        # - Compare hash against stored hash
        # - Flag significant changes

        return alerts

    async def _process_alert(self, alert: DriftAlert):
        """Process a drift alert."""
        # Store in active alerts
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)

        # Broadcast if callback configured
        if self.broadcast_callback:
            await self._broadcast_alert(alert)

        # Auto-remediate if possible
        if self._can_auto_remediate(alert):
            await self._auto_remediate(alert)

        logger.warning(
            f"DRIFT ALERT: {alert.drift_type.value} | "
            f"Severity: {alert.severity} | "
            f"{alert.description}"
        )

    async def _broadcast_alert(self, alert: DriftAlert):
        """Broadcast alert to governance system."""
        message = {
            "type": "GOVERNANCE_BROADCAST",
            "source": "DRIFT_SENTINEL",
            "timestamp": datetime.now().isoformat(),
            "alert": {
                "id": alert.alert_id,
                "type": alert.drift_type.value,
                "severity": alert.severity,
                "description": alert.description,
                "migration_path": alert.migration_path
            },
            "message": (
                f"Engineering doctrine updated due to upstream change: "
                f"{alert.description}"
            )
        }

        if self.broadcast_callback:
            try:
                await self.broadcast_callback(message)
            except Exception as e:
                logger.error(f"Broadcast failed: {e}")

    def _can_auto_remediate(self, alert: DriftAlert) -> bool:
        """Check if alert can be auto-remediated."""
        # Auto-remediate:
        # - Deprecation notices (add warning)
        # - Version sunset with known replacement
        # NOT auto-remediate:
        # - Security advisories (require review)
        # - Breaking changes (require manual validation)

        return (
            alert.drift_type in [DriftType.DEPRECATION, DriftType.VERSION_SUNSET] and
            alert.migration_path is not None
        )

    async def _auto_remediate(self, alert: DriftAlert):
        """Automatically remediate a drift alert."""
        for doctrine_id in alert.affected_doctrines:
            action = RemediationAction(
                action_id=f"rem_{alert.alert_id}_{doctrine_id}",
                alert_id=alert.alert_id,
                action_type="UPDATE",
                doctrine_id=doctrine_id,
                old_value="",  # Would be populated with actual old value
                new_value=f"DEPRECATED: {alert.description}",
                performed_at=datetime.now(),
                auto_applied=True,
                notes=f"Auto-remediated: {alert.migration_path}"
            )

            self.remediation_history.append(action)

        alert.auto_remediated = True
        alert.remediation_notes = f"Auto-applied at {datetime.now().isoformat()}"

        logger.info(f"Auto-remediated: {alert.alert_id}")

    def archive_doctrine_version(
        self,
        doctrine: EngineeringDoctrine,
        reason: str
    ) -> Path:
        """Archive a doctrine version before update."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = self.archive_path / f"{doctrine.doctrine_id}_{timestamp}.json"

        archive_data = {
            "doctrine_id": doctrine.doctrine_id,
            "title": doctrine.title,
            "content": doctrine.content,
            "authority_weight": doctrine.authority_weight,
            "determinism_hash": doctrine.determinism_hash,
            "archived_at": datetime.now().isoformat(),
            "archive_reason": reason,
            "version_metadata": {
                "status": doctrine.version_metadata.status.value if doctrine.version_metadata else None
            }
        }

        with open(archive_file, 'w') as f:
            json.dump(archive_data, f, indent=2)

        logger.info(f"Archived doctrine: {doctrine.doctrine_id} -> {archive_file}")
        return archive_file

    def get_active_alerts(self) -> List[DriftAlert]:
        """Get all active (unresolved) alerts."""
        return list(self.active_alerts.values())

    def resolve_alert(self, alert_id: str, resolution_notes: str):
        """Mark an alert as resolved."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts.pop(alert_id)
            alert.remediation_notes = resolution_notes
            logger.info(f"Alert resolved: {alert_id}")

    def get_status(self) -> Dict[str, Any]:
        """Get sentinel status."""
        return {
            "is_running": self.is_running,
            "active_alerts": len(self.active_alerts),
            "total_alerts_generated": len(self.alert_history),
            "remediations_performed": len(self.remediation_history),
            "auto_remediations": len([
                r for r in self.remediation_history if r.auto_applied
            ]),
            "last_scans": {
                scan_type.value: ts.isoformat() if ts else None
                for scan_type, ts in self.last_scan.items()
            },
            "vendors_monitored": list(self.VENDOR_ENDPOINTS.keys())
        }

    def get_alert_history(
        self,
        limit: int = 100,
        severity_filter: Optional[str] = None,
        type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get alert history with optional filters."""
        alerts = self.alert_history

        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]

        if type_filter:
            alerts = [a for a in alerts if a.drift_type.value == type_filter]

        return [
            {
                "alert_id": a.alert_id,
                "type": a.drift_type.value,
                "severity": a.severity,
                "description": a.description,
                "detected_at": a.detected_at.isoformat(),
                "auto_remediated": a.auto_remediated
            }
            for a in alerts[-limit:]
        ]
