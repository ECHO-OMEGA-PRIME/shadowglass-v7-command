"""
PIE PHASE COMMIT LEDGER INTEGRATION
Governance Directive: PATCH DIRECTIVE - Phase Commit Reporting

Writes PHASE_COMMIT events to OMNISCIENT only after:
1. All tests pass
2. Phase is declared COMPLETE

NO auth logic changes. NO API changes. NO ingestion.
"""

import subprocess
import hashlib
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not available - phase commits will be logged only")


OMNISCIENT_URL = "https://omniscient-sync.bmcii1976.workers.dev"


class PhaseStatus(Enum):
    """Phase completion status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class AuditStatus(Enum):
    """Audit verification status."""
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


class EnforcementMode(Enum):
    """Security enforcement mode."""
    FAIL_CLOSED = "FAIL_CLOSED"
    FAIL_OPEN = "FAIL_OPEN"


@dataclass
class PhaseCommitEvent:
    """Phase commit event for OMNISCIENT ledger."""
    engine_name: str
    phase_id: str
    status: str
    commit_hashes: list[str]
    audit_status: str
    enforcement_mode: str
    rollback_anchor: str
    timestamp: str
    tests_passed: int
    tests_total: int
    test_output_hash: Optional[str] = None


def get_current_commit_hash() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent
        )
        return result.stdout.strip()[:12]
    except Exception as e:
        logger.warning(f"Could not get commit hash: {e}")
        return "unknown"


def get_recent_commits(count: int = 5) -> list[str]:
    """Get recent commit hashes."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--format=%H"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent
        )
        return [h[:12] for h in result.stdout.strip().split("\n") if h]
    except Exception as e:
        logger.warning(f"Could not get recent commits: {e}")
        return []


def hash_test_output(output: str) -> str:
    """Create deterministic hash of test output."""
    return hashlib.sha256(output.encode()).hexdigest()[:16]


def run_phase_tests(test_module: str) -> tuple[bool, int, int, str]:
    """
    Run tests for a phase.

    Returns:
        Tuple of (all_passed, passed_count, total_count, output)
    """
    try:
        result = subprocess.run(
            ["python", test_module],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent.parent,
            timeout=300
        )

        output = result.stdout + result.stderr

        # Parse test results from output
        # Look for "Passed: X" and "Total: Y" patterns
        passed = 0
        total = 0

        for line in output.split("\n"):
            if "Passed:" in line:
                try:
                    passed = int(line.split("Passed:")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            if "Total:" in line:
                try:
                    total = int(line.split("Total:")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass

        all_passed = result.returncode == 0 and passed == total and total > 0

        return all_passed, passed, total, output

    except subprocess.TimeoutExpired:
        logger.error("Test execution timed out")
        return False, 0, 0, "TIMEOUT"
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return False, 0, 0, str(e)


def write_phase_commit(event: PhaseCommitEvent) -> bool:
    """
    Write phase commit event to OMNISCIENT ledger.

    GUARDED: Only writes if status is COMPLETE and audit is PASS.

    Returns:
        True if write succeeded
    """
    # GUARD: Only write if phase is COMPLETE
    if event.status != PhaseStatus.COMPLETE.value:
        logger.warning(f"PHASE_COMMIT blocked: status is {event.status}, not COMPLETE")
        return False

    # GUARD: Only write if audit passed
    if event.audit_status != AuditStatus.PASS.value:
        logger.warning(f"PHASE_COMMIT blocked: audit_status is {event.audit_status}, not PASS")
        return False

    # GUARD: Tests must have actually passed
    if event.tests_passed != event.tests_total or event.tests_total == 0:
        logger.warning(
            f"PHASE_COMMIT blocked: tests {event.tests_passed}/{event.tests_total}"
        )
        return False

    # Prepare payload
    payload = {
        "event_type": "PHASE_COMMIT",
        "source": "PIE",
        **asdict(event)
    }

    logger.info(f"PHASE_COMMIT: {event.engine_name}/{event.phase_id} → OMNISCIENT")

    if not HAS_REQUESTS:
        logger.warning("requests unavailable - logging event only")
        logger.info(f"PHASE_COMMIT_EVENT: {json.dumps(payload, indent=2)}")
        return True

    try:
        response = requests.post(
            f"{OMNISCIENT_URL}/governance/phase-commit",
            json=payload,
            timeout=30
        )

        if response.status_code in [200, 201]:
            logger.info(f"PHASE_COMMIT written to ledger: {response.json()}")
            return True
        else:
            logger.warning(
                f"PHASE_COMMIT ledger returned {response.status_code}: {response.text}"
            )
            # Still return True - we logged it locally
            return True

    except requests.RequestException as e:
        logger.warning(f"PHASE_COMMIT network error (event logged locally): {e}")
        # Log locally as fallback
        logger.info(f"PHASE_COMMIT_EVENT_LOCAL: {json.dumps(payload, indent=2)}")
        return True


def complete_phase(
    phase_id: str,
    test_modules: list[str],
    enforcement_mode: EnforcementMode = EnforcementMode.FAIL_CLOSED
) -> tuple[bool, Optional[PhaseCommitEvent]]:
    """
    Complete a PIE phase with full verification.

    Steps:
    1. Run all test modules
    2. Verify all pass
    3. Write PHASE_COMMIT to OMNISCIENT

    Args:
        phase_id: Phase identifier (e.g., "WEEK_1_API_ENFORCEMENT")
        test_modules: List of test module paths to run
        enforcement_mode: Security enforcement mode

    Returns:
        Tuple of (success, event or None)
    """
    logger.info(f"PIE PHASE COMPLETION: {phase_id}")
    logger.info(f"Running {len(test_modules)} test module(s)...")

    total_passed = 0
    total_tests = 0
    all_outputs = []
    all_success = True

    for module in test_modules:
        logger.info(f"Running: {module}")
        success, passed, total, output = run_phase_tests(module)

        total_passed += passed
        total_tests += total
        all_outputs.append(output)

        if not success:
            logger.error(f"TEST FAILURE: {module} ({passed}/{total})")
            all_success = False

    # Combine outputs for hash
    combined_output = "\n".join(all_outputs)
    output_hash = hash_test_output(combined_output)

    # Determine status
    if all_success and total_passed == total_tests and total_tests > 0:
        status = PhaseStatus.COMPLETE
        audit_status = AuditStatus.PASS
    else:
        status = PhaseStatus.FAILED
        audit_status = AuditStatus.FAIL

    # Build event
    event = PhaseCommitEvent(
        engine_name="PIE",
        phase_id=phase_id,
        status=status.value,
        commit_hashes=get_recent_commits(3),
        audit_status=audit_status.value,
        enforcement_mode=enforcement_mode.value,
        rollback_anchor=get_current_commit_hash(),
        timestamp=datetime.utcnow().isoformat() + "Z",
        tests_passed=total_passed,
        tests_total=total_tests,
        test_output_hash=output_hash
    )

    # Write to ledger (guarded - will block if not COMPLETE/PASS)
    if status == PhaseStatus.COMPLETE:
        write_phase_commit(event)
        logger.info(f"PHASE {phase_id}: COMPLETE")
        return True, event
    else:
        logger.error(f"PHASE {phase_id}: FAILED ({total_passed}/{total_tests})")
        return False, event
