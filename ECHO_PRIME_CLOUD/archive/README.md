# ARCHIVE LAYER

**Authority:** 11.0 SOVEREIGN
**Classification:** Custody Only

---

## PURPOSE

The Archive Layer provides **custody-only** storage for all Echo Prime data. It stores bytes, maintains integrity, and routes to appropriate tiers.

**Philosophy:** Archive never reasons. Archive never interprets. Archive is pure custody.

---

## COMPONENTS

| Component | Responsibility |
|-----------|----------------|
| **343 Guilty Spark** | Hash, compress, deduplicate, version, ledger |
| **ASF (Archival Storage Facility)** | Route to tiers, manage lifecycle, interface with cloud |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ARCHIVE LAYER                                   │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                   343 GUILTY SPARK                              │    │
│   │                   (Stateless Archiver)                          │    │
│   │                                                                 │    │
│   │   Hash → Compress → Deduplicate → Version → Ledger → Route     │    │
│   │                                                                 │    │
│   │   HOLDS: ZERO credentials                                       │    │
│   │   KNOWS: ZERO bucket names                                      │    │
│   │   CAN: NEVER list storage                                       │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│                              ▼                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │              ARCHIVAL STORAGE FACILITY (ASF)                    │    │
│   │                                                                 │    │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │    │
│   │   │   HOT   │  │  WARM   │  │  COLD   │  │  DEEP   │          │    │
│   │   │  NVMe   │  │   HDD   │  │   B2    │  │   B2    │          │    │
│   │   │ 7 days  │  │ 30 days │  │ 1 year  │  │ Forever │          │    │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘          │    │
│   │                                                                 │    │
│   │   HOLDS: ALL cloud credentials                                  │    │
│   │   KNOWS: Bucket names, endpoints                                │    │
│   │   CAN: List, read, write storage                               │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## INPUTS

| Input | Source | Format |
|-------|--------|--------|
| Blob write requests | Memory layer | Hash + bytes + tier |
| Blob read requests | Memory layer | Hash |
| Lifecycle triggers | Scheduler | Timer events |
| Verify requests | Memory layer | Hash |

---

## OUTPUTS

| Output | Destination | Format |
|--------|-------------|--------|
| Opaque storage URIs | Memory layer | `asf://tier/hash` |
| Blob data | Memory layer | Bytes |
| Verification results | Memory layer | Boolean |
| Ledger entries | Local storage | JSONL |

---

## INVARIANTS

| Invariant | Enforcement |
|-----------|-------------|
| **Archive never reasons** | No ML/LLM in archive layer |
| **Archive never interprets content** | Treats all as opaque bytes |
| **343 GS never holds credentials** | Architectural separation |
| **All operations logged to ledger** | Append-only ledger |
| **Hash-addressed only** | No filename-based access |
| **Immutable once written** | Write-once semantics |

---

## BOUNDARY ENFORCEMENT

### Who Can Access Archive

| Component | Access Level |
|-----------|--------------|
| Memory Layer | Hash-addressed read/write via 343 GS |
| Engines (TIE, LIE, etc.) | **BLOCKED** - HTTP 403 |
| API Layer | **BLOCKED** |
| Analysis Layer | **BLOCKED** |

### 343 GS → ASF Interface

```python
# 343 GS talks to ASF via HTTP
# ASF validates origin before processing

gateway.write_blob(hash, bytes, tier) -> opaque_uri
gateway.read_blob(hash) -> bytes
gateway.verify_blob(hash) -> bool
gateway.promote(hash, from_tier, to_tier) -> bool
```

### Blocked Access Pattern

```python
# Engine attempting direct access = BLOCKED
X-Component-Origin: TIE  # Engine origin
POST /gateway/write      # Storage operation

# Result: HTTP 403 Forbidden
# Logged to: boundary_violations.jsonl
```

---

## FAILURE MODES

| Failure | Detection | Response | Recovery |
|---------|-----------|----------|----------|
| Cloud unavailable | Health check | Queue locally | Retry on recovery |
| Hash mismatch | Verification | Reject + alert | Retrieve from replica |
| Storage full | Threshold | Fail-safe mode | Expand or migrate |
| Credential expiry | Auth failure | Rotate credentials | Auto-rotate |
| Ledger corruption | Checksum | Halt writes | Restore from backup |

### Fail-Safe States

| State | Trigger | Cloud | Local | Ledger |
|-------|---------|-------|-------|--------|
| NORMAL | All healthy | ✅ | ✅ | ✅ |
| DEGRADED | 3 cloud failures | Retry | ✅ | ✅ |
| OFFLINE | 10 cloud failures | Queue | ✅ | ✅ |
| PRESERVATION | Storage full | Queue | Write-only | ✅ |

---

## SECURITY NOTES

### Credential Isolation

- **Only ASF** may hold cloud credentials
- Credentials loaded from isolated vault at startup
- Never exposed in logs, responses, or errors
- Rotated automatically on schedule

### Encryption

- All data encrypted before storage
- DEK from Prometheus Vault per object
- Encrypted DEK stored with object
- KEK never leaves Vault

### Audit Trail

Every operation generates a ledger entry:

```json
{
  "timestamp": "2026-02-03T06:30:00Z",
  "operation": "WRITE",
  "hash": "sha256:abc123...",
  "tier": "COLD",
  "size_bytes": 1048576,
  "compressed_bytes": 524288,
  "deduplicated": false,
  "outcome": "SUCCESS"
}
```

---

## SUBDIRECTORIES

| Directory | Contents |
|-----------|----------|
| `guilty_spark/` | 343 Guilty Spark implementation |
| `asf/` | Archival Storage Facility implementation |

---

**Document Version:** 1.0.0
**Created:** 2026-02-03
