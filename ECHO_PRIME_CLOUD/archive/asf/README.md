# ARCHIVAL STORAGE FACILITY (ASF)

**Authority:** 11.0 SOVEREIGN
**Classification:** Storage Router

---

## PURPOSE

The Archival Storage Facility is the **only component** that interfaces with cloud storage. It holds credentials, routes to tiers, and manages storage lifecycle.

**Philosophy:** ASF is infrastructure. ASF holds credentials. ASF never reasons.

---

## RESPONSIBILITIES

| Task | Implementation |
|------|----------------|
| **Hold credentials** | Isolated credential vault |
| **Route to tiers** | Policy-based routing |
| **Manage lifecycle** | Automated tier migration |
| **Interface with B2** | S3-compatible API |
| **Return opaque URIs** | No bucket names exposed |

---

## WHAT ASF DOES NOT DO

| Forbidden | Reason |
|-----------|--------|
| ❌ Interpret content | Pure custody |
| ❌ Make decisions | No intelligence |
| ❌ Cache data | Stateless routing |
| ❌ Expose credentials | Security |
| ❌ Serve engines directly | Boundary enforcement |

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ARCHIVAL STORAGE FACILITY (ASF)                       │
│                              Port 9344                                   │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                     GATEWAY ROUTER                              │    │
│   │                                                                 │    │
│   │   POST /gateway/write    → Write blob to tier                  │    │
│   │   GET  /gateway/read/{h} → Read blob by hash                   │    │
│   │   GET  /gateway/verify/{h} → Check blob exists                 │    │
│   │   POST /gateway/promote  → Move between tiers                  │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                   CREDENTIAL VAULT                              │    │
│   │                                                                 │    │
│   │   B2_ENDPOINT        → s3.us-east-005.backblazeb2.com          │    │
│   │   B2_ACCESS_KEY_ID   → ****                                    │    │
│   │   B2_SECRET_ACCESS_KEY → ****                                  │    │
│   │                                                                 │    │
│   │   ISOLATED | AUDITED | NEVER EXPOSED                           │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                              │                                           │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                    STORAGE TIERS                                │    │
│   │                                                                 │    │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────────┐  ┌─────────────┐  │    │
│   │   │   HOT   │  │  WARM   │  │    COLD     │  │    DEEP     │  │    │
│   │   │  NVMe   │  │   HDD   │  │  B2 bucket  │  │  B2 bucket  │  │    │
│   │   │ 7 days  │  │ 30 days │  │   1 year    │  │   Forever   │  │    │
│   │   └─────────┘  └─────────┘  └─────────────┘  └─────────────┘  │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## INPUTS

| Input | Source | Format |
|-------|--------|--------|
| Write requests | 343 GS only | HTTP POST |
| Read requests | 343 GS only | HTTP GET |
| Verify requests | 343 GS only | HTTP GET |
| Promote requests | 343 GS only | HTTP POST |

**Important:** All requests MUST have `X-Component-Origin: 343_GUILTY_SPARK`

---

## OUTPUTS

| Output | Destination | Format |
|--------|-------------|--------|
| Opaque URIs | 343 GS | `asf://tier/hash` |
| Blob data | 343 GS | Bytes |
| Verification | 343 GS | Boolean |
| Ledger entries | Local | JSONL |

---

## INVARIANTS

| Invariant | Enforcement |
|-----------|-------------|
| **Only 343 GS may access** | Origin validation |
| **Credentials never exposed** | Isolation + audit |
| **URIs are opaque** | No bucket names in responses |
| **All ops logged** | Ledger middleware |
| **Fail closed on error** | Explicit deny policy |

---

## STORAGE TIERS

| Tier | Location | Retention | Cost | Access |
|------|----------|-----------|------|--------|
| HOT | Local NVMe | 7 days | $0 | Instant |
| WARM | Local HDD | 30 days | $0 | Fast |
| COLD | B2 asf-cold | 365 days | $6/TB/mo | Minutes |
| DEEP | B2 asf-deep | Forever | $6/TB/mo | Minutes |

### Lifecycle Flow

```
HOT (7d) → WARM (30d) → COLD (365d) → DEEP (forever)
```

Automatic migration based on age and access patterns.

---

## BACKBLAZE B2 CONFIGURATION

| Property | Value |
|----------|-------|
| Endpoint | `s3.us-east-005.backblazeb2.com` |
| Region | `us-east-005` |
| Cold Bucket | `asf-cold-archive` |
| Deep Bucket | `asf-deep-archive` |

### S3 Protocol

ASF uses S3-compatible API:

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://s3.us-east-005.backblazeb2.com',
    region_name='us-east-005',
    aws_access_key_id=cred.access_key,
    aws_secret_access_key=cred.secret_key
)

# Put object (hash-addressed)
s3.put_object(
    Bucket='asf-cold-archive',
    Key=f'sha256/{hash}',
    Body=data
)
```

---

## CREDENTIAL ISOLATION

```python
class CredentialVault:
    """
    ONLY class that may access cloud credentials.
    All access audited to credential_access.jsonl
    """

    def get_client(self) -> boto3.client:
        """
        Returns configured S3 client.
        Credentials loaded from isolated .env
        Never exposed in logs or responses.
        """
        self._audit_access()
        return self._create_client()
```

### Credential Rules

| Rule | Enforcement |
|------|-------------|
| Never in logs | Log sanitization |
| Never in responses | Response filtering |
| Never in errors | Error sanitization |
| Rotated quarterly | Automated rotation |
| Audited always | Access logging |

---

## GATEWAY API

### Write Blob

```http
POST /gateway/write
X-Component-Origin: 343_GUILTY_SPARK
Content-Type: application/json

{
  "hash": "sha256:abc123...",
  "tier": "COLD",
  "data_base64": "..."
}

Response:
{
  "uri_opaque": "asf://cold/abc123...",
  "success": true
}
```

### Read Blob

```http
GET /gateway/read/sha256:abc123...
X-Component-Origin: 343_GUILTY_SPARK

Response:
<binary data>
```

### Verify Blob

```http
GET /gateway/verify/sha256:abc123...
X-Component-Origin: 343_GUILTY_SPARK

Response:
{
  "exists": true,
  "tier": "COLD"
}
```

### Promote Blob

```http
POST /gateway/promote
X-Component-Origin: 343_GUILTY_SPARK
Content-Type: application/json

{
  "hash": "sha256:abc123...",
  "from_tier": "COLD",
  "to_tier": "HOT"
}

Response:
{
  "success": true,
  "new_uri": "asf://hot/abc123..."
}
```

---

## FAILURE MODES

| Failure | Detection | Response | Recovery |
|---------|-----------|----------|----------|
| B2 unavailable | Connection error | Queue locally | Retry |
| Auth failure | 403 response | Alert + rotate | New credentials |
| Bucket missing | 404 response | Halt + alert | Create bucket |
| Write failure | S3 error | Retry 3x | Fail-safe mode |
| Credential expiry | Auth error | Auto-rotate | New credentials |

### Fail-Safe States

| State | Condition | Behavior |
|-------|-----------|----------|
| NORMAL | All healthy | Full operations |
| DEGRADED | 3 failures | Retry with backoff |
| OFFLINE | 10 failures | Queue to local |
| PRESERVATION | Storage full | Read-only |

---

## SECURITY NOTES

### Origin Validation

```python
@router.post("/gateway/write")
async def write_blob(request: Request, data: WriteRequest):
    origin = request.headers.get("X-Component-Origin")

    if origin != "343_GUILTY_SPARK":
        await emit_violation(origin, "write")
        raise HTTPException(403, "Access denied")

    # Process write...
```

### Audit Logging

All operations logged:

```json
{
  "timestamp": "2026-02-03T06:30:00Z",
  "operation": "WRITE",
  "origin": "343_GUILTY_SPARK",
  "hash": "sha256:abc123...",
  "tier": "COLD",
  "bucket": "***REDACTED***",
  "outcome": "SUCCESS"
}
```

---

## FILES

| File | Purpose |
|------|---------|
| `gateway_router.py` | HTTP API endpoints |
| `credential_isolation.py` | Credential vault |
| `tier_manager.py` | Storage tier logic |
| `lifecycle.py` | Automated migration |
| `storage_policies.yaml` | Policy configuration |

---

**Document Version:** 1.0.0
**Created:** 2026-02-03
