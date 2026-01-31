# Tax Intelligence Engine

**Deterministic Authority-Weighted Reasoning System**

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/bmcwilliams4/tax-intelligence-engine/releases)
[![Authority Hardening](https://img.shields.io/badge/authority--hardening-verified-green.svg)](#authority-hardening-layer)
[![Determinism](https://img.shields.io/badge/determinism-26%2F26%20tests-brightgreen.svg)](#testing-strategy)

---

## Overview

A reasoning engine designed for **auditability** and **determinism** in tax knowledge retrieval. The system eliminates black-box behavior by ensuring every conclusion is traceable to primary legal authority.

Built for professional reliance by CPAs, attorneys, and audit defense teams.

**Core Guarantee:** Identical queries produce identical reasoning paths, verifiable via cryptographic hashing.

---

## Architectural Principles

### Determinism

Every query is processed through a normalized pipeline:

```
Input → Normalize → Match → Weight → Hash → Respond
```

The `determinism_hash` field in each response allows verification that the same inputs will always produce the same outputs. Hash computation uses SHA-256 over the normalized query, matched doctrine key, and sorted candidate list.

### Authority Weighting

Tax conclusions derive from sources with varying legal weight. The engine applies a hierarchical scoring model:

| Authority Level       | Weight | Examples                          |
|-----------------------|--------|-----------------------------------|
| Internal Revenue Code | 100    | IRC §162, §263A, §199A            |
| Treasury Regulations  | 80     | Treas. Reg. §1.162-1              |
| Court Precedent       | 60     | Exacto Spring, Watson v. US      |
| IRS Guidance          | 40     | Revenue Procedures, Rulings      |
| Publications          | 20     | IRS Pub 535, Pub 946              |

This hierarchy reflects how positions are evaluated in audit and litigation contexts. Higher-authority sources control when conflicts exist.

### Conflict Resolution

When multiple doctrines score within 80% of the top candidate, the engine surfaces the conflict explicitly rather than selecting silently. The response includes:

- Primary doctrine selected
- Competing doctrines considered
- Resolution rationale
- Confidence differential

This design prioritizes transparency over convenience.

### Audit Replay

All queries are logged with their determinism hash. Given a hash, the original reasoning path can be reconstructed. This supports:

- Professional liability documentation
- Historical query analysis
- Consistency verification across time

### Telemetry

A telemetry spine captures:

- Query trace IDs (8-character hash identifiers)
- Layer timing (doctrine matching, vector search, response generation)
- Error logging with stack traces
- Reasoning snapshots at decision points

Telemetry data is file-based for simplicity and portability.

---

## Authority Hardening Layer (v1.1.0)

This release implements a hardened cognition layer focused on professional-grade reliability.

**Components:**

| Component                 | Description                                           |
|---------------------------|-------------------------------------------------------|
| Conflict Detection        | 80% threshold for surfacing competing doctrines       |
| Precedent Anchoring       | Binds conclusions to controlling case law             |
| Confidence Stratification | Four-tier risk classification per conclusion          |
| Determinism Hashing       | SHA-256 verification of reasoning consistency         |
| Whitespace Normalization  | Regex-based query normalization for stable matching   |

**Confidence Stratification:**

| Level                   | Meaning                              |
|-------------------------|--------------------------------------|
| `defensible`            | Position fully supportable           |
| `aggressive_supportable`| Arguable, document rationale         |
| `disclosure_recommended`| Form 8275 disclosure advisable       |
| `high_audit_risk`       | Significant controversy potential    |

---

## Testing Strategy

The adversarial test suite validates deterministic behavior across 9 categories:

| Test Category              | Purpose                                    | Status |
|----------------------------|--------------------------------------------|--------|
| Repeated Identical Queries | Same query 10x returns identical hash      | Pass   |
| Case Sensitivity           | `QUERY` = `query` = `Query`                | Pass   |
| Whitespace Normalization   | Tabs, double-spaces, leading/trailing      | Pass   |
| Multi-Doctrine Conflicts   | Competing doctrine resolution consistency  | Pass   |
| Edge Cases                 | Empty, special characters, long queries    | Pass   |
| Concurrent Queries         | 20 simultaneous requests, thread safety    | Pass   |
| Authority Weight Stability | Consistent weighting across runs           | Pass   |
| Response Mode Independence | Mode selection doesn't affect doctrine     | Pass   |
| Semantic Equivalence       | Related phrasings match same doctrine      | Pass   |

**Result:** 26/26 tests pass.

---

## Query Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              QUERY LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User Query                                                             │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────┐                                                    │
│  │ Normalize       │  lowercase, collapse whitespace, trim             │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ Doctrine Match  │  keyword scoring against 84 doctrine topics       │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ Authority Weight│  aggregate source weights (IRC=100...Pub=20)      │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ Conflict Check  │  surface if multiple doctrines within 80%         │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ Compute Hash    │  SHA-256(normalized_query|topic_key|candidates)   │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ Telemetry Log   │  trace_id, timing, decision points                │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  Auditable Response                                                     │
│  {                                                                      │
│    "doctrine_match": true,                                              │
│    "authority_weight": 320,                                             │
│    "confidence_stratification": "defensible",                           │
│    "controlling_precedent": "Exacto Spring Corp v. Commissioner",       │
│    "determinism_hash": "45a462a6069d9432",                              │
│    "conflict_detected": false                                           │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Why This Exists

Most AI reasoning systems operate as black boxes. A question goes in, an answer comes out, and the path between them is opaque. For domains with legal or financial consequences, this opacity is unacceptable.

This system explores a different architecture: **inspectable machine judgment**. Every conclusion carries its provenance—the sources consulted, the conflicts detected, the authority weights applied. The goal is not to replace professional judgment but to make AI-assisted reasoning auditable enough to support it.

---

## Engineering Approach

- **Governance tagging** — semantic versioning with annotated release notes
- **Rollback-safe releases** — no partial states, all dependencies resolved
- **Audit-first design** — logging and traceability precede features
- **Determinism verification** — adversarial testing before each release
- **Production telemetry** — observability built into the core loop

---

## Future Direction

Potential extensions under consideration:

- Multi-domain reasoning (expanding beyond tax to regulatory compliance)
- Programmable doctrine engines (user-defined authority hierarchies)
- Citation graph analysis (precedent relationship mapping)
- Temporal versioning (how would this query resolve under 2020 law?)

These remain speculative. The current focus is stability and reliability.

---

## Setup

### Requirements

- Python 3.11+
- Dependencies: `fastapi`, `uvicorn`, `chromadb`, `sentence-transformers`, `loguru`

### Installation

```bash
pip install fastapi uvicorn chromadb sentence-transformers loguru requests
```

### Running

```bash
cd TAX_KNOWLEDGE
python tax_intelligence_engine.py
```

Server starts on `http://localhost:8391`

### Health Check

```bash
curl http://localhost:8391/health
```

### Example Query

```bash
curl -X POST http://localhost:8391/tax/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is reasonable compensation for S-corp shareholders?", "mode": "fast"}'
```

---

## API Endpoints

| Endpoint                           | Method | Description                       |
|------------------------------------|--------|-----------------------------------|
| `/health`                          | GET    | Service health and uptime         |
| `/tax/query`                       | POST   | Primary query interface           |
| `/hardening/verify-determinism`    | POST   | Verify hash consistency           |
| `/hardening/authority-weights`     | GET    | Retrieve weight hierarchy         |
| `/hardening/confidence-stratification` | GET | Get stratification definitions |

---

## Repository Structure

```
TAX_KNOWLEDGE/
├── tax_intelligence_engine.py   # Core engine (84 doctrine topics)
├── tax_telemetry.py             # Telemetry infrastructure
├── tax_doctrine_cache.py        # Pre-built doctrine knowledge
├── adversarial_authority_test.py# Determinism test suite
├── tax_expert_search.py         # Vector search interface
├── tax_expert_service.py        # Service orchestration
├── tax_expert_api.py            # API layer
├── test_hardening.ps1           # PowerShell verification
├── test_whitespace_fix.py       # Normalization validation
└── README.md
```

---

## License

Proprietary. Not for redistribution.

---

## Version History

| Version | Date       | Description                                |
|---------|------------|--------------------------------------------|
| 1.2.0   | 2026-01-30 | Cognitive Stability - Semantic Normalization |
| 1.1.0   | 2026-01-30 | Authority Hardening Layer                  |
| 1.0.0   | 2026-01-29 | Initial release with 84 doctrine topics    |

---

*Deterministic reasoning infrastructure for professional tax practice.*
