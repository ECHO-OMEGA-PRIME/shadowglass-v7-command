"""
PIE PHASE COMMIT GUARD TESTS
Governance Directive: PATCH DIRECTIVE - Phase Commit Reporting

Proves:
1. Ledger write BLOCKED when status != COMPLETE
2. Ledger write BLOCKED when audit_status != PASS
3. Ledger write BLOCKED when tests_passed != tests_total
4. Ledger write ALLOWED only when ALL guards pass
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add PIE to path
pie_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(pie_root.parent))

from PIE.governance.phase_commit import (
    PhaseCommitEvent,
    PhaseStatus,
    AuditStatus,
    EnforcementMode,
    write_phase_commit,
)


def create_test_event(
    status: str = "COMPLETE",
    audit_status: str = "PASS",
    tests_passed: int = 10,
    tests_total: int = 10
) -> PhaseCommitEvent:
    """Create a test event with configurable fields."""
    return PhaseCommitEvent(
        engine_name="PIE",
        phase_id="TEST_PHASE",
        status=status,
        commit_hashes=["abc123"],
        audit_status=audit_status,
        enforcement_mode="FAIL_CLOSED",
        rollback_anchor="abc123",
        timestamp=datetime.utcnow().isoformat() + "Z",
        tests_passed=tests_passed,
        tests_total=tests_total,
        test_output_hash="test_hash"
    )


def test_guard_blocks_incomplete_status():
    """Test: status != COMPLETE → write BLOCKED."""
    event = create_test_event(status="PENDING")

    # Should return False without attempting write
    result = write_phase_commit(event)

    assert result is False, "Should block when status is not COMPLETE"
    print("✓ TEST PASSED: INCOMPLETE status blocks ledger write")


def test_guard_blocks_failed_status():
    """Test: status == FAILED → write BLOCKED."""
    event = create_test_event(status="FAILED")

    result = write_phase_commit(event)

    assert result is False, "Should block when status is FAILED"
    print("✓ TEST PASSED: FAILED status blocks ledger write")


def test_guard_blocks_failed_audit():
    """Test: audit_status != PASS → write BLOCKED."""
    event = create_test_event(audit_status="FAIL")

    result = write_phase_commit(event)

    assert result is False, "Should block when audit_status is not PASS"
    print("✓ TEST PASSED: FAILED audit blocks ledger write")


def test_guard_blocks_pending_audit():
    """Test: audit_status == PENDING → write BLOCKED."""
    event = create_test_event(audit_status="PENDING")

    result = write_phase_commit(event)

    assert result is False, "Should block when audit_status is PENDING"
    print("✓ TEST PASSED: PENDING audit blocks ledger write")


def test_guard_blocks_partial_tests():
    """Test: tests_passed < tests_total → write BLOCKED."""
    event = create_test_event(tests_passed=8, tests_total=10)

    result = write_phase_commit(event)

    assert result is False, "Should block when not all tests pass"
    print("✓ TEST PASSED: Partial test pass blocks ledger write")


def test_guard_blocks_zero_tests():
    """Test: tests_total == 0 → write BLOCKED."""
    event = create_test_event(tests_passed=0, tests_total=0)

    result = write_phase_commit(event)

    assert result is False, "Should block when no tests ran"
    print("✓ TEST PASSED: Zero tests blocks ledger write")


def test_guard_allows_complete_pass():
    """Test: All guards pass → write ALLOWED."""
    event = create_test_event(
        status="COMPLETE",
        audit_status="PASS",
        tests_passed=10,
        tests_total=10
    )

    # Mock requests to avoid actual network call
    with patch("PIE.governance.phase_commit.HAS_REQUESTS", True):
        with patch("PIE.governance.phase_commit.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "test_id"}
            mock_requests.post.return_value = mock_response

            result = write_phase_commit(event)

            assert result is True, "Should allow write when all guards pass"
            # Verify the request was made
            mock_requests.post.assert_called_once()

    print("✓ TEST PASSED: All guards pass → ledger write ALLOWED")


def test_write_only_after_all_pass():
    """
    Integration test: Prove ledger write only occurs after ALL conditions met.

    This is the key test proving the guard behavior.
    """
    # Scenario 1: Complete but failed audit
    event1 = create_test_event(status="COMPLETE", audit_status="FAIL")
    assert write_phase_commit(event1) is False, "Scenario 1 should block"

    # Scenario 2: Passed audit but incomplete
    event2 = create_test_event(status="IN_PROGRESS", audit_status="PASS")
    assert write_phase_commit(event2) is False, "Scenario 2 should block"

    # Scenario 3: Complete, passed audit, but partial tests
    event3 = create_test_event(
        status="COMPLETE",
        audit_status="PASS",
        tests_passed=5,
        tests_total=10
    )
    assert write_phase_commit(event3) is False, "Scenario 3 should block"

    # Scenario 4: ALL conditions met
    event4 = create_test_event(
        status="COMPLETE",
        audit_status="PASS",
        tests_passed=10,
        tests_total=10
    )

    with patch("PIE.governance.phase_commit.HAS_REQUESTS", True):
        with patch("PIE.governance.phase_commit.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "test_id"}
            mock_requests.post.return_value = mock_response

            result = write_phase_commit(event4)
            assert result is True, "Scenario 4 should allow"
            mock_requests.post.assert_called_once()

    print("✓ TEST PASSED: Ledger write ONLY occurs when ALL conditions met")


def run_all_tests():
    """Run all phase commit guard tests."""
    print("=" * 70)
    print("PIE PHASE COMMIT GUARD TESTS")
    print("Proving: Ledger write ONLY after ALL tests pass")
    print("=" * 70)
    print()

    tests = [
        ("Guard: INCOMPLETE status", test_guard_blocks_incomplete_status),
        ("Guard: FAILED status", test_guard_blocks_failed_status),
        ("Guard: FAILED audit", test_guard_blocks_failed_audit),
        ("Guard: PENDING audit", test_guard_blocks_pending_audit),
        ("Guard: Partial tests", test_guard_blocks_partial_tests),
        ("Guard: Zero tests", test_guard_blocks_zero_tests),
        ("Allow: All guards pass", test_guard_allows_complete_pass),
        ("Integration: Write only after ALL pass", test_write_only_after_all_pass),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nRunning: {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {name}")
            print(f"  Error: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 70)

    if failed == 0:
        print()
        print("✓ ALL TESTS PASSED")
        print("✓ LEDGER WRITE GUARDS VERIFIED")
        print("✓ WRITE ONLY OCCURS AFTER ALL TESTS PASS")
        return 0
    else:
        print()
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
