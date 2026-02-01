"""
PIE Ingest Endpoint Authentication Test
Governance Directive: PATCH DIRECTIVE - Integration Test

Proves:
1. Unauthenticated requests are REJECTED (401)
2. Rejection happens BEFORE handler execution
3. Valid auth allows request through
"""

import sys
from pathlib import Path

# Add PIE to path
pie_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(pie_root.parent))

from fastapi.testclient import TestClient
from PIE.api.endpoints import app
from PIE.api.dependencies import generate_test_token


client = TestClient(app, raise_server_exceptions=False)


def test_ingest_rejects_missing_auth():
    """
    Test: POST /engineering/ingest WITHOUT auth headers → 401

    This proves:
    1. Request is rejected
    2. Rejection is 401 (not 500 or other)
    3. Handler never executes (no path validation error)
    """
    response = client.post(
        "/engineering/ingest",
        json={
            "source_path": "/nonexistent/path/that/would/fail/if/handler/ran",
            "recursive": True
        }
    )

    # Must be 401 Unauthorized
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    # Check error detail mentions authentication
    detail = response.json().get("detail", "")
    assert "MISSING" in detail.upper() or "AUTH" in detail.upper(), \
        f"Expected auth-related error, got: {detail}"

    print("INTEGRATION TEST PASSED: Missing auth → 401 BEFORE handler")


def test_ingest_rejects_invalid_token():
    """
    Test: POST /engineering/ingest WITH invalid token → 401
    """
    response = client.post(
        "/engineering/ingest",
        json={
            "source_path": "/nonexistent/path",
            "recursive": True
        },
        headers={
            "X-PIE-Actor-ID": "test_actor",
            "X-PIE-Token": "80:invalid_signature_here",
            "X-PIE-Timestamp": "9999999999"
        }
    )

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("INTEGRATION TEST PASSED: Invalid token → 401")


def test_ingest_rejects_insufficient_authority():
    """
    Test: POST /engineering/ingest WITH TIER_60 → 403 Forbidden
    """
    # Generate valid token but with insufficient authority
    token, timestamp = generate_test_token("low_tier_actor", authority_tier=60)

    response = client.post(
        "/engineering/ingest",
        json={
            "source_path": "/nonexistent/path",
            "recursive": True
        },
        headers={
            "X-PIE-Actor-ID": "low_tier_actor",
            "X-PIE-Token": token,
            "X-PIE-Timestamp": str(timestamp)
        }
    )

    # Must be 403 Forbidden (not 401)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print("INTEGRATION TEST PASSED: Insufficient authority → 403")


def test_ingest_accepts_valid_tier_80():
    """
    Test: POST /engineering/ingest WITH valid TIER_80 → passes auth

    Note: Will get 404 for path (handler executes), proving auth passed.
    """
    token, timestamp = generate_test_token("valid_actor", authority_tier=80)

    response = client.post(
        "/engineering/ingest",
        json={
            "source_path": "/nonexistent/path/proves/handler/ran",
            "recursive": True
        },
        headers={
            "X-PIE-Actor-ID": "valid_actor",
            "X-PIE-Token": token,
            "X-PIE-Timestamp": str(timestamp)
        }
    )

    # Should NOT be 401/403 - auth passed, handler ran
    # Will be 404 (path not found) or 500 (engine init) - either proves auth worked
    assert response.status_code not in [401, 403], \
        f"Auth should have passed, but got {response.status_code}"

    print(f"INTEGRATION TEST PASSED: Valid TIER_80 → auth passed (got {response.status_code})")


def run_all_tests():
    """Run all integration tests."""
    print("=" * 70)
    print("PIE INGEST AUTHENTICATION INTEGRATION TESTS")
    print("Proving: Rejection happens BEFORE handler execution")
    print("=" * 70)
    print()

    tests = [
        ("Missing auth → 401", test_ingest_rejects_missing_auth),
        ("Invalid token → 401", test_ingest_rejects_invalid_token),
        ("Insufficient authority → 403", test_ingest_rejects_insufficient_authority),
        ("Valid TIER_80 → passes auth", test_ingest_accepts_valid_tier_80),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nRunning: {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name}")
            print(f"  Error: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} passed")
    print("=" * 70)

    if failed == 0:
        print("ALL INTEGRATION TESTS PASSED")
        print("SECURITY ENFORCEMENT VERIFIED: Auth checked BEFORE handler")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
