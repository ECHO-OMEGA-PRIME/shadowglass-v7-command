# CANONICAL MEMORY LAYER

**Authority:** 11.0 SOVEREIGN
**Classification:** Canonical Truth

---

## PURPOSE

The Memory Layer is the **single source of truth** for all intelligence operations. Engines read from memory. Engines write to memory. Memory is governed, versioned, and audited.

**Philosophy:** Memory is centralized. Memory is governed. Memory is the bridge between archive and intelligence.

---

## COMPONENTS

| Component | Purpose |
|-----------|---------|
| **Crystal Memory** | Immutable historical truth |
| **9-Pillar Memory** | Governed intelligence memory |
| **Time Graph** | Temporal relationships |
| **Provenance Index** | Source tracking |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CANONICAL MEMORY                                  │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                    CRYSTAL MEMORY                               │    │
│   │                                                                 │    │
│   │   Immutable │ Versioned │ Hash-Addressed │ Time-Indexed        │    │
│   │                                                                 │    │
│   │   Tax Law │ Case Law │ Land Records │ Financial │ Compliance   │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                   9-PILLAR MEMORY                               │    │
│   │                                                                 │    │
│   │   1. Tax │ 2. Legal │ 3. Land │ 4. Financial │ 5. Compliance   │    │
│   │   6. Business │ 7. Personal │ 8. Historical │ 9. Meta          │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                     TIME GRAPH                                  │    │
│   │                                                                 │    │
│   │   Temporal relationships │ Effective dates │ Version chains    │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │                  PROVENANCE INDEX                               │    │
│   │                                                                 │    │
│   │   Source tracking │ Citation chains │ Authority levels         │    │
│   └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## INPUTS

| Input | Source | Format |
|-------|--------|--------|
| Read requests | Engines | Query spec |
| Write requests | Engines | Data + metadata |
| Archive retrieval | 343 GS | Hash + bytes |
| Time queries | Analysis | Temporal spec |

---

## OUTPUTS

| Output | Destination | Format |
|--------|-------------|--------|
| Query results | Engines | Structured data |
| Archive requests | 343 GS | Hash + bytes |
| Audit logs | Vault | JSONL |
| Provenance chains | Engines | Graph |

---

## INVARIANTS

| Invariant | Enforcement |
|-----------|-------------|
| **Memory is centralized** | Single service |
| **Memory is governed** | Access policies |
| **Memory is versioned** | Immutable versions |
| **Memory is audited** | All access logged |
| **Memory owns archive access** | 343 GS interface |

---

## ACCESS PATTERNS

### Engine → Memory (ALLOWED)

```python
# Engine requests data
result = memory.query(
    pillar="tax",
    query="IRC Section 162 deductions",
    time_range=(2020, 2025)
)
```

### Engine → Archive (BLOCKED)

```python
# Engine attempts direct archive access
# BLOCKED by boundary enforcement
archive.read(hash="sha256:...")  # HTTP 403
```

### Memory → Archive (ALLOWED)

```python
# Memory retrieves from archive via 343 GS
data = gateway.read_blob(hash="sha256:...")
```

---

## CRYSTAL MEMORY

Immutable historical truth with hash-addressed storage.

### Structure

```
crystal/
├── tax/
│   ├── irc/
│   │   ├── sections/
│   │   └── regulations/
│   └── cases/
├── legal/
│   ├── statutes/
│   └── cases/
├── land/
│   ├── mineral/
│   └── surface/
└── meta/
    ├── schemas/
    └── indexes/
```

### Versioning

Every entry is versioned with immutable history:

```json
{
  "hash": "sha256:abc123...",
  "version": 3,
  "effective_date": "2025-01-01",
  "supersedes": "sha256:def456...",
  "provenance": {
    "source": "IRS Publication 544",
    "authority": 0.95
  }
}
```

---

## 9-PILLAR MEMORY

Governed intelligence memory organized by domain.

| Pillar | Domain | Contents |
|--------|--------|----------|
| 1 | Tax | IRC, regulations, cases, positions |
| 2 | Legal | Statutes, cases, precedents |
| 3 | Land | Mineral/surface chains, conveyances |
| 4 | Financial | Transactions, valuations |
| 5 | Compliance | Audits, filings, deadlines |
| 6 | Business | Entities, contracts, operations |
| 7 | Personal | Individual records (encrypted) |
| 8 | Historical | Time-series, archives |
| 9 | Meta | Schemas, indexes, governance |

---

## TIME GRAPH

Temporal relationship tracking for versioned data.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          TIME GRAPH                                      │
│                                                                          │
│   2020 ────────── 2021 ────────── 2022 ────────── 2023 ─────── 2024    │
│     │               │               │               │               │    │
│     ▼               ▼               ▼               ▼               ▼    │
│   [IRC v1]      [IRC v2]       [IRC v3]       [IRC v4]       [IRC v5]   │
│                     │                             │                      │
│                     └──── supersedes ────────────┘                      │
│                                                                          │
│   Query: "IRC as of 2022-06-15" → Returns IRC v2                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Temporal Queries

```python
# Query effective at specific date
result = memory.query(
    pillar="tax",
    topic="depreciation",
    as_of="2022-06-15"
)

# Query version history
history = memory.history(
    pillar="tax",
    topic="depreciation"
)
```

---

## PROVENANCE INDEX

Track source and authority for all data.

```json
{
  "entry_hash": "sha256:abc123...",
  "provenance": {
    "source_type": "primary",
    "source_url": "https://www.irs.gov/...",
    "retrieved_at": "2026-01-15T10:30:00Z",
    "authority_level": 0.99,
    "citations": [
      {"type": "statute", "ref": "26 USC 162"},
      {"type": "regulation", "ref": "26 CFR 1.162-1"}
    ]
  }
}
```

### Authority Levels

| Level | Source | Trust |
|-------|--------|-------|
| 0.99+ | Primary statute/regulation | Absolute |
| 0.90-0.98 | Official guidance | Very high |
| 0.80-0.89 | Court decisions | High |
| 0.70-0.79 | Secondary sources | Medium |
| 0.60-0.69 | Commentary | Lower |
| <0.60 | Unverified | Flag required |

---

## FAILURE MODES

| Failure | Detection | Response | Recovery |
|---------|-----------|----------|----------|
| Memory unavailable | Health check | Engines halt | Wait for recovery |
| Archive unavailable | 343 GS error | Use cached | Retry on recovery |
| Version conflict | Hash mismatch | Reject write | Reconcile |
| Provenance gap | Validation | Flag entry | Manual review |

---

## SECURITY NOTES

### Access Control

| Component | Memory Access |
|-----------|---------------|
| Engines | Read/Write (scoped) |
| Analysis | Read only |
| API | Read only (filtered) |
| Archive | Via 343 GS only |
| Vault | Encryption keys |

### Encryption

- Personal data (Pillar 7) encrypted at rest
- DEK per entry from Vault
- Memory layer handles encryption/decryption

### Audit

All access logged:

```json
{
  "timestamp": "2026-02-03T06:30:00Z",
  "operation": "QUERY",
  "component": "ENGINE_TIE",
  "pillar": "tax",
  "query_hash": "sha256:...",
  "results_count": 15,
  "duration_ms": 42
}
```

---

**Document Version:** 1.0.0
**Created:** 2026-02-03
