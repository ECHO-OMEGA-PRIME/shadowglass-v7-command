# PIE PHASE COMMIT LEDGER INTEGRATION
## Governance Directive: Phase Commit Reporting

**Directive ID:** PIE_PHASE_COMMIT_2026-02-01
**Classification:** GOVERNANCE_INTEGRATION
**Status:** IMPLEMENTED

---

## OVERVIEW

PIE integrates with OMNISCIENT Phase Commit Ledger to record verified phase completions.

**Key Principle:** Ledger writes are GUARDED - only occur after ALL tests pass.

---

## PHASE COMMIT EVENT STRUCTURE

```json
{
  "event_type": "PHASE_COMMIT",
  "source": "PIE",
  "engine_name": "PIE",
  "phase_id": "WEEK_1_API_ENFORCEMENT",
  "status": "COMPLETE",
  "commit_hashes": ["9a0a35e", "040c365", "239628b"],
  "audit_status": "PASS",
  "enforcement_mode": "FAIL_CLOSED",
  "rollback_anchor": "9a0a35e",
  "timestamp": "2026-02-01T02:00:00Z",
  "tests_passed": 23,
  "tests_total": 23,
  "test_output_hash": "a1b2c3d4e5f6g7h8"
}
```

---

## GUARDS (ENFORCED)

Ledger write is **BLOCKED** unless:

| Condition | Required Value |
|-----------|----------------|
| `status` | `COMPLETE` |
| `audit_status` | `PASS` |
| `tests_passed` | `== tests_total` |
| `tests_total` | `> 0` |

If any guard fails, the event is **NOT written** to OMNISCIENT.

---

## USAGE

### Complete a Phase

```python
from PIE.governance import complete_phase, EnforcementMode

success, event = complete_phase(
    phase_id="WEEK_1_API_ENFORCEMENT",
    test_modules=[
        "CORE/PIE/tests/security/test_hardening_week1.py",
        "CORE/PIE/tests/api/test_ingest_auth.py"
    ],
    enforcement_mode=EnforcementMode.FAIL_CLOSED
)

if success:
    print(f"Phase complete: {event.rollback_anchor}")
else:
    print(f"Phase failed: {event.tests_passed}/{event.tests_total}")
```

### Manual Event Write (Guarded)

```python
from PIE.governance import write_phase_commit, PhaseCommitEvent

event = PhaseCommitEvent(
    engine_name="PIE",
    phase_id="WEEK_1_API_ENFORCEMENT",
    status="COMPLETE",  # Must be COMPLETE
    commit_hashes=["9a0a35e"],
    audit_status="PASS",  # Must be PASS
    enforcement_mode="FAIL_CLOSED",
    rollback_anchor="9a0a35e",
    timestamp="2026-02-01T02:00:00Z",
    tests_passed=23,  # Must equal tests_total
    tests_total=23    # Must be > 0
)

# Will only write if all guards pass
success = write_phase_commit(event)
```

---

## OMNISCIENT ENDPOINT

**URL:** `https://omniscient-sync.bmcii1976.workers.dev/governance/phase-commit`

**Method:** POST

**Fallback:** If network unavailable, event is logged locally.

---

## PHASE DEFINITIONS

| Phase ID | Tests | Status |
|----------|-------|--------|
| `WEEK_1_HARDENING` | test_hardening_week1.py | COMPLETE |
| `WEEK_1_API_ENFORCEMENT` | test_ingest_auth.py | COMPLETE |

---

## ROLLBACK ANCHOR

The `rollback_anchor` field contains the git commit hash at phase completion.

If a phase must be rolled back:
```bash
git revert <rollback_anchor>
```

---

## AUDIT TRAIL

All phase commits are logged via `loguru`:

| Event | Log Level |
|-------|-----------|
| Phase start | INFO |
| Test module run | INFO |
| Test failure | ERROR |
| Guard blocked | WARNING |
| Ledger write | INFO |
| Network error | WARNING |

---

## CONSTRAINTS

This integration does NOT:
- Change authentication logic
- Change APIs
- Add ingestion capability
- Modify schemas

It ONLY:
- Writes verified phase completions to OMNISCIENT
- Guards writes behind test passage

---

**PIE: Phase commits are earned, not declared.**
