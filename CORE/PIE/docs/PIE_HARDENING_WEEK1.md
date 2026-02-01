# PIE HARDENING — WEEK 1 SECURITY NOTES
## Governance Directive Implementation

**Directive ID:** PIE_HARDENING_WEEK1_2026-02-01
**Classification:** SECURITY_HARDENING
**State:** ENGINEERING_OBSERVER_STATE
**Status:** IMPLEMENTED

---

## EXECUTIVE SUMMARY

Week 1 critical fixes implement FAIL CLOSED security for PIE ingestion:

| Fix | Status | Behavior |
|-----|--------|----------|
| Authentication middleware | ✓ IMPLEMENTED | 401 on missing/invalid credentials |
| Authority override disabled | ✓ REMOVED | No bypass mechanism exists |
| Path allowlist enforcement | ✓ IMPLEMENTED | Reject paths outside allowlist |
| Signed manifest verification | ✓ IMPLEMENTED | Reject on hash/signature mismatch |

**FAIL CLOSED is the default and only behavior.**

---

## 1. AUTHENTICATION MIDDLEWARE

### File: `security/auth_middleware.py`

### Implementation

```python
class PIEAuthMiddleware:
    """
    FAIL CLOSED authentication for POST /engineering/ingest
    """
    MIN_INGEST_AUTHORITY = 80  # TIER_80 minimum
    TOKEN_VALIDITY_SECONDS = 300  # 5 minutes
```

### Required Credentials

| Field | Required | Description |
|-------|----------|-------------|
| `actor_id` | YES | Unique actor identifier |
| `token` | YES | Signed authentication token |
| `timestamp` | YES | Request timestamp (for expiration) |

### Token Format

```
{authority_tier}:{hmac_signature}

Signature = HMAC-SHA256(signing_key, actor_id:timestamp:authority_tier)
```

### Rejection Conditions

| Condition | Result Code | HTTP Equivalent |
|-----------|-------------|-----------------|
| Missing actor_id | `MISSING_ACTOR_ID` | 401 Unauthorized |
| Missing token | `MISSING_TOKEN` | 401 Unauthorized |
| Invalid signature | `INVALID_TOKEN` | 401 Unauthorized |
| Expired token | `EXPIRED_TOKEN` | 401 Unauthorized |
| Authority < 80 | `INSUFFICIENT_AUTHORITY` | 403 Forbidden |
| Any error | `FAIL_CLOSED` | 401 Unauthorized |

### Security Properties

- **No default signing key** — must be explicitly provided
- **Constant-time comparison** — prevents timing attacks
- **Token expiration** — 5 minute validity window
- **Authority enforcement** — TIER_80+ required for ingestion

---

## 2. AUTHORITY_OVERRIDE: PERMANENTLY DISABLED

### File: `security/hardening_config.py`

### Removed Code Paths

The following have been **permanently removed**:

| Function | Previous Behavior | Current Status |
|----------|-------------------|----------------|
| `check_authority_override()` | Checked env var | **REMOVED** |
| `apply_override_token()` | Bypassed auth | **REMOVED** |
| `emergency_bypass()` | Admin bypass | **REMOVED** |
| `set_override_flag()` | Runtime flag | **REMOVED** |
| `get_override_status()` | Status check | **REMOVED** |

### Enforcement

```python
AUTHORITY_OVERRIDE_DISABLED: Final[bool] = True

# In PIEHardeningConfig.__post_init__:
if self.authority_override_enabled:
    raise ValueError("SECURITY VIOLATION: authority_override cannot be enabled")
```

### How to Modify (If Required)

1. Modify source code in `hardening_config.py`
2. Pass code review
3. Redeploy PIE
4. Document change with Commander approval

**There are NO runtime toggles or environment variables.**

---

## 3. FILESYSTEM PATH ALLOWLIST

### File: `security/path_validator.py`

### Allowlist Definition

```python
PIE_ARTIFACT_ALLOWLIST = [
    "O:/ECHO_OMEGA_PRIME/CORE/PIE/corpus",
    "O:/ECHO_OMEGA_PRIME/CORE/PIE/staging/artifacts",
    "O:/ECHO_OMEGA_PRIME/CORE/PIE/external/approved",
]
```

### Validation Rules

| Check | Behavior |
|-------|----------|
| Empty path | REJECT |
| Path traversal (`..`) | REJECT |
| Symlink (direct) | REJECT |
| Symlink (in hierarchy) | REJECT |
| Outside allowlist | REJECT |
| Resolution failure | REJECT (fail closed) |

### Rejection Codes

| Code | Meaning |
|------|---------|
| `REJECTED_NOT_IN_ALLOWLIST` | Path not under allowed base |
| `REJECTED_SYMLINK` | Symlink detected |
| `REJECTED_PATH_TRAVERSAL` | `..` in path |
| `REJECTED_INVALID_PATH` | Cannot parse path |
| `REJECTED_FAIL_CLOSED` | Error during validation |

### Security Properties

- **No wildcards** — explicit paths only
- **Symlink rejection** — both direct and in hierarchy
- **Path traversal blocking** — checked before resolution
- **Defense in depth** — multiple validation layers

---

## 4. SIGNED MANIFEST VERIFICATION

### File: `security/manifest_verifier.py`

### Manifest Structure

```json
{
  "artifact_id": "unique_identifier",
  "artifact_type": "CONTROL_CATALOG",
  "sha256_hash": "64_hex_characters",
  "file_size": 12345,
  "created_at": "2026-02-01T00:00:00Z",
  "signed_by": "signer_identifier",
  "signature": "hmac_sha256_signature",
  "metadata": {}
}
```

### Signature Computation

```
message = artifact_id:artifact_type:sha256_hash:file_size:created_at:signed_by
signature = HMAC-SHA256(signing_key, message)
```

### Verification Steps

1. Check manifest file exists
2. Parse JSON (fail on syntax error)
3. Validate required fields present
4. Verify HMAC signature
5. Compute SHA-256 of artifact
6. Compare computed hash to manifest hash

### Rejection Codes

| Code | Meaning |
|------|---------|
| `MISSING_MANIFEST` | No manifest file |
| `INVALID_MANIFEST_FORMAT` | JSON parse error |
| `MISSING_REQUIRED_FIELD` | Field not present |
| `INVALID_SIGNATURE` | HMAC mismatch |
| `HASH_MISMATCH` | Content hash differs |
| `ARTIFACT_NOT_FOUND` | Artifact file missing |
| `FAIL_CLOSED` | Any verification error |

---

## 5. TEST COVERAGE

### File: `tests/security/test_hardening_week1.py`

### Test Cases

| Test | Validates |
|------|-----------|
| `test_auth_missing_actor_id` | 401 on missing actor |
| `test_auth_missing_token` | 401 on missing token |
| `test_auth_invalid_token` | 401 on bad signature |
| `test_auth_expired_token` | 401 on expired token |
| `test_auth_insufficient_authority` | 403 on TIER < 80 |
| `test_auth_valid_tier_80` | Success for TIER_80 |
| `test_auth_valid_tier_100` | Success for Commander |
| `test_auth_no_signing_key` | Fail closed |
| `test_authority_override_disabled` | Override removed |
| `test_path_empty_allowlist` | Fail closed |
| `test_path_outside_allowlist` | Reject external paths |
| `test_path_traversal` | Reject `..` |
| `test_path_valid_in_allowlist` | Accept valid paths |
| `test_manifest_missing` | Reject missing manifest |
| `test_manifest_hash_mismatch` | Reject wrong hash |
| `test_manifest_valid` | Accept valid manifest |
| `test_manifest_no_signing_key` | Fail closed |
| `test_hardening_verification` | Config valid |
| `test_fail_closed_config` | Cannot disable |

### Running Tests

```bash
cd O:/ECHO_OMEGA_PRIME
python CORE/PIE/tests/security/test_hardening_week1.py
```

---

## 6. AUDIT TRAIL

All security events are logged via `loguru`:

| Event | Log Level | Example |
|-------|-----------|---------|
| Auth success | INFO | `AUTH_SUCCESS: actor=X, tier=80` |
| Auth failure | WARNING | `AUTH_FAIL: Missing token for actor=X` |
| Path valid | INFO | `PATH_VALID: /path (allowlist: /base)` |
| Path rejected | WARNING | `PATH_REJECT: Path not in allowlist` |
| Manifest valid | INFO | `MANIFEST_VALID: artifact_id` |
| Manifest rejected | WARNING | `MANIFEST_REJECT: Hash mismatch` |

---

## 7. DEPLOYMENT CHECKLIST

Before deploying Week 1 hardening:

- [ ] Generate signing key (minimum 32 bytes)
- [ ] Configure allowlist paths (create directories if needed)
- [ ] Run test suite (all 19 tests must pass)
- [ ] Verify `AUTHORITY_OVERRIDE_DISABLED = True`
- [ ] Verify `fail_closed = True`
- [ ] Review audit log configuration

---

## 8. CONSTRAINTS SATISFIED

| Constraint | Status |
|------------|--------|
| No artifact ingestion | ✓ |
| No data analysis | ✓ |
| No schema changes beyond auth + validation | ✓ |
| All changes auditable | ✓ |
| FAIL CLOSED behavior | ✓ |

---

## VERSION HISTORY

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-02-01 | Initial hardening implementation |

---

**ECHO OMEGA PRIME | Authority 11.0 SOVEREIGN**
**PIE: Hardened. Fail Closed. No Override.**
