"""
PIE HARDENING TESTS — WEEK 1
Governance Directive: Week 1 Critical Fixes
Classification: SECURITY_HARDENING

Tests proving FAIL CLOSED behavior for:
1. Authentication middleware
2. Authority override disabled
3. Path allowlist enforcement
4. Signed manifest verification
"""

import os
import sys
import json
import time
import tempfile
from pathlib import Path

# Add PIE to path
pie_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(pie_root.parent))

from PIE.security import (
    PIEAuthMiddleware,
    AuthResult,
    create_auth_middleware,
    PIEPathValidator,
    PathValidationResult,
    create_path_validator,
    PIEManifestVerifier,
    ManifestResult,
    create_manifest_verifier,
    PIEHardeningConfig,
    get_hardening_config,
    verify_hardening_active,
    AUTHORITY_OVERRIDE_DISABLED,
)


# Test signing key (32 bytes)
TEST_SIGNING_KEY = b"test_signing_key_32_bytes_long!!"


def test_auth_missing_actor_id():
    """Test: Missing actor_id → REJECT (401 equivalent)."""
    middleware = create_auth_middleware(TEST_SIGNING_KEY)

    result = middleware.authenticate(
        actor_id=None,
        token="100:fake_token"
    )

    assert not result.valid
    assert result.result == AuthResult.MISSING_ACTOR_ID
    print("✓ TEST PASSED: Missing actor_id rejected")


def test_auth_missing_token():
    """Test: Missing token → REJECT (401 equivalent)."""
    middleware = create_auth_middleware(TEST_SIGNING_KEY)

    result = middleware.authenticate(
        actor_id="test_actor",
        token=None
    )

    assert not result.valid
    assert result.result == AuthResult.MISSING_TOKEN
    print("✓ TEST PASSED: Missing token rejected")


def test_auth_invalid_token():
    """Test: Invalid token signature → REJECT."""
    middleware = create_auth_middleware(TEST_SIGNING_KEY)

    result = middleware.authenticate(
        actor_id="test_actor",
        token="100:invalid_signature_here"
    )

    assert not result.valid
    assert result.result == AuthResult.INVALID_TOKEN
    print("✓ TEST PASSED: Invalid token rejected")


def test_auth_expired_token():
    """Test: Expired token → REJECT."""
    middleware = create_auth_middleware(TEST_SIGNING_KEY)

    # Generate token with old timestamp
    old_timestamp = int(time.time()) - 600  # 10 minutes ago
    token = middleware.generate_token("test_actor", 100, old_timestamp)

    result = middleware.authenticate(
        actor_id="test_actor",
        token=token,
        timestamp=old_timestamp
    )

    assert not result.valid
    assert result.result == AuthResult.EXPIRED_TOKEN
    print("✓ TEST PASSED: Expired token rejected")


def test_auth_insufficient_authority():
    """Test: Authority below TIER_80 → REJECT."""
    middleware = create_auth_middleware(TEST_SIGNING_KEY)

    # Generate token with TIER_60 (below minimum)
    timestamp = int(time.time())
    token = middleware.generate_token("test_actor", 60, timestamp)

    result = middleware.authenticate(
        actor_id="test_actor",
        token=token,
        timestamp=timestamp
    )

    assert not result.valid
    assert result.result == AuthResult.INSUFFICIENT_AUTHORITY
    print("✓ TEST PASSED: Insufficient authority rejected")


def test_auth_valid_tier_80():
    """Test: Valid TIER_80 token → ACCEPT."""
    middleware = create_auth_middleware(TEST_SIGNING_KEY)

    timestamp = int(time.time())
    token = middleware.generate_token("test_actor", 80, timestamp)

    result = middleware.authenticate(
        actor_id="test_actor",
        token=token,
        timestamp=timestamp
    )

    assert result.valid
    assert result.result == AuthResult.SUCCESS
    assert result.authority_tier == 80
    print("✓ TEST PASSED: Valid TIER_80 accepted")


def test_auth_valid_tier_100():
    """Test: Valid TIER_100 (Commander) token → ACCEPT."""
    middleware = create_auth_middleware(TEST_SIGNING_KEY)

    timestamp = int(time.time())
    token = middleware.generate_token("commander", 100, timestamp)

    result = middleware.authenticate(
        actor_id="commander",
        token=token,
        timestamp=timestamp
    )

    assert result.valid
    assert result.result == AuthResult.SUCCESS
    assert result.authority_tier == 100
    print("✓ TEST PASSED: Valid TIER_100 accepted")


def test_auth_no_signing_key():
    """Test: No signing key → FAIL to create middleware."""
    try:
        create_auth_middleware(None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "signing_key" in str(e).lower()
        print("✓ TEST PASSED: No signing key fails closed")


def test_authority_override_disabled():
    """Test: Authority override is PERMANENTLY DISABLED."""
    assert AUTHORITY_OVERRIDE_DISABLED is True

    config = get_hardening_config()
    assert config.authority_override_enabled is False

    # Attempting to create config with override enabled should fail
    try:
        PIEHardeningConfig(authority_override_enabled=True)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "authority_override" in str(e).lower()
        print("✓ TEST PASSED: Authority override permanently disabled")


def test_path_empty_allowlist():
    """Test: Empty allowlist → FAIL to create validator."""
    try:
        create_path_validator([])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "allowlist" in str(e).lower()
        print("✓ TEST PASSED: Empty allowlist fails closed")


def test_path_outside_allowlist():
    """Test: Path outside allowlist → REJECT."""
    # Create validator with specific allowlist
    validator = PIEPathValidator([tempfile.gettempdir()])

    # Try to access path outside allowlist
    result = validator.validate("C:/Windows/System32/config")

    assert not result.valid
    assert result.result == PathValidationResult.REJECTED_NOT_IN_ALLOWLIST
    print("✓ TEST PASSED: Path outside allowlist rejected")


def test_path_traversal():
    """Test: Path traversal attempt → REJECT."""
    validator = PIEPathValidator([tempfile.gettempdir()])

    result = validator.validate(f"{tempfile.gettempdir()}/../../../etc/passwd")

    assert not result.valid
    assert result.result == PathValidationResult.REJECTED_PATH_TRAVERSAL
    print("✓ TEST PASSED: Path traversal rejected")


def test_path_valid_in_allowlist():
    """Test: Valid path in allowlist → ACCEPT."""
    temp_dir = tempfile.gettempdir()
    validator = PIEPathValidator([temp_dir])

    # Create a test file
    test_file = Path(temp_dir) / "pie_test_file.txt"
    test_file.write_text("test")

    try:
        result = validator.validate(str(test_file))
        assert result.valid
        assert result.result == PathValidationResult.VALID
        print("✓ TEST PASSED: Valid path in allowlist accepted")
    finally:
        test_file.unlink()


def test_manifest_missing():
    """Test: Missing manifest → REJECT."""
    verifier = create_manifest_verifier(TEST_SIGNING_KEY)

    # Create artifact without manifest
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(b'{"test": "data"}')
        artifact_path = f.name

    try:
        result = verifier.verify(artifact_path)
        assert not result.valid
        assert result.result == ManifestResult.MISSING_MANIFEST
        print("✓ TEST PASSED: Missing manifest rejected")
    finally:
        os.unlink(artifact_path)


def test_manifest_hash_mismatch():
    """Test: Hash mismatch → REJECT."""
    verifier = create_manifest_verifier(TEST_SIGNING_KEY)

    # Create artifact
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(b'{"test": "data"}')
        artifact_path = f.name

    # Create manifest with wrong hash
    manifest_path = f"{artifact_path}.manifest.json"
    manifest = {
        "artifact_id": "test_artifact",
        "artifact_type": "CONTROL_CATALOG",
        "sha256_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "file_size": 100,
        "created_at": "2026-02-01T00:00:00Z",
        "signed_by": "test_signer",
        "signature": "fake_signature"
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f)

    try:
        result = verifier.verify(artifact_path)
        # Should fail on either signature or hash mismatch
        assert not result.valid
        assert result.result in [
            ManifestResult.INVALID_SIGNATURE,
            ManifestResult.HASH_MISMATCH
        ]
        print("✓ TEST PASSED: Hash/signature mismatch rejected")
    finally:
        os.unlink(artifact_path)
        os.unlink(manifest_path)


def test_manifest_valid():
    """Test: Valid signed manifest → ACCEPT."""
    verifier = create_manifest_verifier(TEST_SIGNING_KEY)

    # Create artifact
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(b'{"test": "data"}')
        artifact_path = f.name

    # Create valid signed manifest
    manifest = verifier.create_manifest(
        artifact_path=artifact_path,
        artifact_id="test_artifact",
        artifact_type="CONTROL_CATALOG",
        signed_by="test_signer"
    )

    manifest_path = f"{artifact_path}.manifest.json"
    verifier.save_manifest(manifest, manifest_path)

    try:
        result = verifier.verify(artifact_path)
        assert result.valid
        assert result.result == ManifestResult.VALID
        print("✓ TEST PASSED: Valid signed manifest accepted")
    finally:
        os.unlink(artifact_path)
        os.unlink(manifest_path)


def test_manifest_no_signing_key():
    """Test: No signing key → FAIL to create verifier."""
    try:
        create_manifest_verifier(None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "signing_key" in str(e).lower()
        print("✓ TEST PASSED: No signing key fails closed")


def test_hardening_verification():
    """Test: Hardening configuration verification passes."""
    assert verify_hardening_active() is True
    print("✓ TEST PASSED: Hardening verification passes")


def test_fail_closed_config():
    """Test: fail_closed cannot be disabled."""
    try:
        PIEHardeningConfig(fail_closed=False)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "fail_closed" in str(e).lower()
        print("✓ TEST PASSED: fail_closed cannot be disabled")


def run_all_tests():
    """Run all hardening tests."""
    print("=" * 70)
    print("PIE HARDENING TESTS — WEEK 1")
    print("Proving FAIL CLOSED Behavior")
    print("=" * 70)
    print()

    tests = [
        # Authentication tests
        ("Auth: Missing actor_id", test_auth_missing_actor_id),
        ("Auth: Missing token", test_auth_missing_token),
        ("Auth: Invalid token", test_auth_invalid_token),
        ("Auth: Expired token", test_auth_expired_token),
        ("Auth: Insufficient authority", test_auth_insufficient_authority),
        ("Auth: Valid TIER_80", test_auth_valid_tier_80),
        ("Auth: Valid TIER_100", test_auth_valid_tier_100),
        ("Auth: No signing key", test_auth_no_signing_key),

        # Authority override tests
        ("Override: Permanently disabled", test_authority_override_disabled),

        # Path validation tests
        ("Path: Empty allowlist", test_path_empty_allowlist),
        ("Path: Outside allowlist", test_path_outside_allowlist),
        ("Path: Traversal attempt", test_path_traversal),
        ("Path: Valid in allowlist", test_path_valid_in_allowlist),

        # Manifest verification tests
        ("Manifest: Missing", test_manifest_missing),
        ("Manifest: Hash mismatch", test_manifest_hash_mismatch),
        ("Manifest: Valid signed", test_manifest_valid),
        ("Manifest: No signing key", test_manifest_no_signing_key),

        # Hardening config tests
        ("Config: Verification passes", test_hardening_verification),
        ("Config: fail_closed enforced", test_fail_closed_config),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nRunning: {name}")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ TEST FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ TEST ERROR: {name}")
            print(f"  Error: {e}")
            failed += 1

    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print()
        print("✓ ALL TESTS PASSED")
        print("✓ FAIL CLOSED BEHAVIOR VERIFIED")
        print("✓ AUTHORITY_OVERRIDE PERMANENTLY DISABLED")
    else:
        print()
        print("✗ SOME TESTS FAILED")
        return 1

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
