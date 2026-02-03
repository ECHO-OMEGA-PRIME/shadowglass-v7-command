# 343 GUILTY SPARK

**Authority:** 11.0 SOVEREIGN
**Classification:** Stateless Archiver

---

## PURPOSE

343 Guilty Spark is the **stateless archiver** component. It processes artifacts for storage without holding credentials or making decisions.

**Philosophy:** Hash. Compress. Deduplicate. Version. Ledger. Route. Nothing more.

---

## RESPONSIBILITIES

| Task | Implementation |
|------|----------------|
| **Hash** | SHA-256 content addressing |
| **Compress** | Zstandard by tier |
| **Deduplicate** | Global hash index lookup |
| **Version** | Immutable version records |
| **Ledger** | Append-only operation log |
| **Route** | Pass to ASF via StorageGateway |

---

## WHAT 343 GS DOES NOT DO

| Forbidden | Reason |
|-----------|--------|
| ❌ Hold credentials | Security boundary |
| ❌ Know bucket names | Abstraction layer |
| ❌ List storage | No enumeration interface |
| ❌ Interpret content | Pure custody |
| ❌ Make decisions | No intelligence |
| ❌ Cache data | Stateless |

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        343 GUILTY SPARK                                  │
│                                                                          │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐ │
│   │   HASH     │───▶│  COMPRESS  │───▶│   DEDUP    │───▶│  VERSION   │ │
│   │  SHA-256   │    │   zstd     │    │   lookup   │    │   record   │ │
│   └────────────┘    └────────────┘    └────────────┘    └────────────┘ │
│                                                                │         │
│                                                                ▼         │
│   ┌────────────┐                                      ┌────────────┐    │
│   │   LEDGER   │◀─────────────────────────────────────│   ROUTE    │    │
│   │  emit log  │                                      │   to ASF   │    │
│   └────────────┘                                      └────────────┘    │
│                                                                          │
│   HOLDS: ZERO credentials    KNOWS: ZERO bucket names                   │
│   CAN: NEVER list storage    STATE: NONE                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## INPUTS

| Input | Source | Format |
|-------|--------|--------|
| Raw artifact | Memory layer | Bytes |
| Target tier | Memory layer | HOT/WARM/COLD/DEEP |
| Metadata | Memory layer | JSON |

---

## OUTPUTS

| Output | Destination | Format |
|--------|-------------|--------|
| Content hash | Memory layer | `sha256:...` |
| Opaque URI | Memory layer | `asf://tier/hash` |
| Ledger entry | Local log | JSONL |
| Compression stats | Memory layer | JSON |

---

## INVARIANTS

| Invariant | Enforcement |
|-----------|-------------|
| **Stateless between requests** | No persistent state |
| **No credential access** | Not in config or code |
| **Hash-addressed only** | No filename operations |
| **All operations logged** | Ledger middleware |
| **Content-blind** | Treats all as opaque bytes |

---

## STORAGE GATEWAY INTERFACE

```python
from gs343.core import create_gateway

gateway = create_gateway("http://localhost:9344")

# Write artifact
result = gateway.write_blob(
    hash="sha256:abc123...",
    data=compressed_bytes,
    tier="COLD"
)
# Returns: WriteResult(uri_opaque="asf://cold/abc123...")

# Read artifact
data = gateway.read_blob(hash="sha256:abc123...")
# Returns: bytes

# Verify artifact
exists = gateway.verify_blob(hash="sha256:abc123...")
# Returns: bool

# Promote tier
promoted = gateway.promote(
    hash="sha256:abc123...",
    from_tier="COLD",
    to_tier="HOT"
)
# Returns: bool
```

---

## COMPRESSION BY TIER

| Tier | Compression | Level | Rationale |
|------|-------------|-------|-----------|
| HOT | zstd | 1 | Speed priority |
| WARM | zstd | 9 | Balanced |
| COLD | zstd | 15 | Size priority |
| DEEP | zstd | 19 | Maximum compression |

---

## DEDUPLICATION

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       DEDUPLICATION FLOW                                 │
│                                                                          │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐                   │
│   │   Hash     │───▶│   Lookup   │───▶│   Found?   │                   │
│   │  compute   │    │   index    │    │            │                   │
│   └────────────┘    └────────────┘    └─────┬──────┘                   │
│                                              │                          │
│                          ┌───────────────────┼───────────────────┐      │
│                          │ YES               │ NO                │      │
│                          ▼                   ▼                   │      │
│                   ┌────────────┐      ┌────────────┐             │      │
│                   │  Return    │      │   Store    │             │      │
│                   │ existing   │      │   new      │             │      │
│                   │   URI      │      │   blob     │             │      │
│                   └────────────┘      └────────────┘             │      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Dedup Index

- SQLite database with hash → uri mapping
- Checked before every write
- Updated after successful writes
- No content stored in index

---

## FAILURE MODES

| Failure | Detection | Response | Recovery |
|---------|-----------|----------|----------|
| Hash mismatch | Verification | Reject | Re-hash source |
| Compression fail | Exception | Fall back to raw | Log + retry |
| ASF unavailable | Connection error | Queue locally | Retry on recovery |
| Index corruption | Checksum | Rebuild index | Scan storage |

---

## SECURITY NOTES

### Boundary Enforcement

343 GS enforces boundaries via BoundaryEnforcer:

```python
# If request comes from engine (TIE, LIE, etc.)
# Request is BLOCKED before reaching ASF

enforcer.validate_origin(request)
# Raises: BoundaryViolation for non-343-GS origins
```

### Audit Trail

Every operation generates ledger entry:

```json
{
  "timestamp": "2026-02-03T06:30:00Z",
  "operation": "ARCHIVE",
  "input_hash": "sha256:abc123...",
  "tier": "COLD",
  "compressed_size": 524288,
  "dedup_hit": false,
  "outcome": "SUCCESS"
}
```

---

## FILES

| File | Purpose |
|------|---------|
| `storage_gateway.py` | Client interface to ASF |
| `boundary_enforcement.py` | Origin validation |
| `compression.py` | Zstd compression |
| `dedup_index.py` | Deduplication lookup |
| `ledger.py` | Operation logging |

---

**Document Version:** 1.0.0
**Created:** 2026-02-03
