# PIE CONTROLLED INGESTION PROTOCOL
## Version 1.0.0 | Classification: GOVERNANCE_TIER_ZERO

**Directive ID:** PIE_INGESTION_PROTOCOL_2026-02-01
**Authority:** Commander Bobby Don McWilliams II
**Status:** PROTOCOL DEFINED — EXECUTION AWAITS AUTHORIZATION

---

## CORE PRINCIPLE

> PIE ingests artifacts, not documents.
> PIE extracts structure, not summaries.
> PIE asks architectural questions, not comprehension questions.

---

## 1. INGESTION PIPELINE

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PIE INGESTION PIPELINE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [Source] ──► [Retrieve] ──► [Verify] ──► [Transform] ──► [Load]    │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Registry │  │ Download │  │ Checksum │  │ Extract  │  │ PIE    │ │
│  │ Lookup   │  │ Artifact │  │ Verify   │  │ Structure│  │ Corpus │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│       │              │              │              │           │     │
│       ▼              ▼              ▼              ▼           ▼     │
│  Source URL     Raw File      Hash Match    Artifact      Indexed   │
│  + Metadata     Downloaded    Confirmed     Classes       + Query   │
│                                                            Ready    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. ARTIFACT TRANSFORMATION

### Input: Raw Source → Output: Structured Artifact

| Input Type | Transformation | Output Structure |
|------------|----------------|------------------|
| PDF Document | Parse → Extract sections → Build hierarchy | Control tree |
| JSON/XML Schema | Validate → Normalize → Index | Schema graph |
| Lockfile | Parse → Resolve transitives → Build graph | Dependency DAG |
| IaC Config | Parse → Extract resources → Map dependencies | Resource graph |
| Postmortem | Parse → Extract timeline → Build cause chain | Failure tree |
| ADR | Parse → Extract decision → Map supersessions | Decision graph |

### Artifact Classes

Each artifact is tagged with ONE PRIMARY class:

```python
class ArtifactClass(Enum):
    DEPENDENCY_STRUCTURE = "dependency_structure"
    VERSION_LIFECYCLE = "version_lifecycle"
    AUTHORITY_HIERARCHY = "authority_hierarchy"
    FAILURE_MODE = "failure_mode"
    CONTROL_MAPPING = "control_mapping"
```

---

## 3. VERSIONING REQUIREMENTS

Every ingested artifact MUST have:

```json
{
  "artifact_id": "string (unique)",
  "corpus": "string (e.g., NIST_800_SERIES)",
  "version": "string (source version)",
  "pie_ingest_version": "1.0.0",
  "ingested_at": "ISO8601 timestamp",
  "source": {
    "url": "string",
    "retrieved_at": "ISO8601 timestamp",
    "sha256": "string (64 hex chars)"
  },
  "provenance": {
    "authority": "string",
    "authority_level": "enum",
    "publication_date": "ISO8601 date",
    "supersedes": "artifact_id or null",
    "superseded_by": "artifact_id or null"
  },
  "artifact_class": "enum",
  "extraction": {
    "extractor_version": "string",
    "extraction_date": "ISO8601 timestamp",
    "node_count": "integer",
    "edge_count": "integer",
    "validation_status": "PASS | FAIL | WARN"
  }
}
```

---

## 4. CHECKSUM VERIFICATION

### Before Ingestion

```python
def verify_artifact(artifact_path: Path, expected_hash: str) -> bool:
    """
    Verify artifact integrity before ingestion.

    FAIL = Do not ingest.
    """
    import hashlib

    with open(artifact_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    if actual_hash != expected_hash:
        logger.error(f"Hash mismatch: expected {expected_hash}, got {actual_hash}")
        return False

    logger.info(f"Hash verified: {actual_hash}")
    return True
```

### Hash Sources

| Source Type | Hash Location |
|-------------|---------------|
| NIST Publications | Listed on download page |
| RFCs | Datatracker metadata |
| GitHub Releases | Release checksums |
| npm Packages | package-lock.json integrity |
| Docker Images | Manifest digest |

---

## 5. PROVENANCE TAGGING

### Authority Levels

| Level | Description | Example |
|-------|-------------|---------|
| `US_FEDERAL_GOVERNMENT` | US Government publications | NIST, CISA |
| `STANDARDS_BODY` | International standards | ISO, IETF, W3C |
| `MAJOR_TECH_COMPANY` | Large tech postmortems | Google, AWS, Meta |
| `OPEN_SOURCE_PROJECT` | OSS project artifacts | Kubernetes, Linux |
| `INDUSTRY_CONSORTIUM` | Industry groups | PCI SSC, HITRUST |
| `ACADEMIC` | Academic publications | ACM, IEEE |

### Provenance Chain

```json
{
  "provenance_chain": [
    {
      "artifact_id": "NIST_SP_800_53_R5",
      "authority": "NIST",
      "supersedes": "NIST_SP_800_53_R4",
      "reason": "Revision update"
    },
    {
      "artifact_id": "NIST_SP_800_53_R4",
      "authority": "NIST",
      "supersedes": "NIST_SP_800_53_R3",
      "reason": "Revision update"
    }
  ]
}
```

---

## 6. CLASS-BY-CLASS INGESTION

### Feed Order (One Class at a Time)

```
Phase 2a: DEPENDENCY_STRUCTURE
  └─► Lockfiles, go.mod, package.json
  └─► Query: "Which dependencies are implicit?"

Phase 2b: VERSION_LIFECYCLE
  └─► Release histories, changelog analysis
  └─► Query: "What would break under version skew?"

Phase 2c: AUTHORITY_HIERARCHY
  └─► RBAC configs, control mappings, ADRs
  └─► Query: "Where is authority undocumented?"

Phase 2d: FAILURE_MODE
  └─► Postmortems, CVE chains, outage reports
  └─► Query: "Which assumptions are unstable?"
```

### Class Isolation Rule

**PIE processes ONE class at a time.**

Do NOT mix:
- Dependency structures with failure modes
- Version lifecycles with authority hierarchies

Keep analysis focused. Cross-class queries come AFTER single-class baselines.

---

## 7. PIE QUERY TEMPLATES

### Dependency Structure Queries
```
"Which components have implicit dependencies not declared in manifests?"
"Which dependency chains would fail silently under partial upgrade?"
"Which transitive dependencies create version conflict risk?"
"Which dependencies are pinned without justification?"
```

### Version Lifecycle Queries
```
"Which version constraints are unstable across releases?"
"What would break under minor version skew?"
"Which deprecation warnings are being ignored?"
"Which LTS assumptions are violated?"
```

### Authority Hierarchy Queries
```
"Where is decision authority implicit but undocumented?"
"Which controls have circular authority dependencies?"
"Which policy conflicts create ambiguous enforcement?"
"Which roles have implicit elevated permissions?"
```

### Failure Mode Queries
```
"Which dependency assumptions are unstable?"
"Which single points of failure are undocumented?"
"Which cascade paths cross trust boundaries?"
"Which recovery procedures have untested dependencies?"
```

---

## 8. PILOT EXECUTION PLAN

### Recommended Pilot: NIST 800-53 Rev 5

**Step 1: Retrieve**
```
Source: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final
Files:
  - sp800-53r5.pdf
  - sp800-53r5-control-catalog.xlsx
  - sp800-53r5-control-catalog.xml (OSCAL format)
```

**Step 2: Verify**
```
Compare SHA-256 against NIST published checksums
Validate OSCAL XML against schema
```

**Step 3: Transform**
```
Extract control hierarchy (Family → Control → Enhancement)
Build control dependency graph (references, incorporates)
Map control baselines (Low, Moderate, High)
```

**Step 4: Load**
```
Index as CONTROL_MAPPING artifact class
Store with full provenance metadata
Enable PIE queries
```

**Step 5: Query**
```
"Which controls have circular dependencies?"
"Where is control authority implicit but undocumented?"
"Which baseline assumptions would break under framework version skew?"
```

---

## 9. ROLLBACK PROTOCOL

### If Ingestion Produces Bad Data

```
1. HALT all PIE queries against affected corpus
2. Identify corrupted artifacts by ingestion batch
3. Rollback to previous corpus version
4. Log rollback reason and affected queries
5. Re-ingest with corrected transformation
6. Validate before re-enabling queries
```

### Rollback Command
```bash
pie-corpus rollback --corpus=NIST_800_SERIES --to-version=1.0.0 --reason="Transform error"
```

---

## 10. INGESTION GATES

### Before ANY Ingestion

| Gate | Requirement | Enforced By |
|------|-------------|-------------|
| Source Registered | In PIE_AUTHORITATIVE_SOURCES.md | Manual check |
| Hash Verified | SHA-256 match | Automated |
| Provenance Tagged | Authority + date + supersession | Automated |
| Single Class | One artifact class per batch | Manual check |
| Commander Notified | Logged to OMNISCIENT | Automated |

### Ingestion NOT Authorized Until

- [ ] Commander explicitly approves pilot corpus
- [ ] Source registry reviewed and approved
- [ ] Transformation logic tested on sample
- [ ] Rollback procedure verified

---

## VERSION HISTORY

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-02-01 | Initial protocol |

---

**ECHO OMEGA PRIME | Authority 11.0 SOVEREIGN**
**PIE: Protocol defined. Awaiting ingestion authorization.**
