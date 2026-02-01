# PIE ARTIFACT INTAKE STAGING PLAN
## Artifact Type: CONTROL_CATALOG

**Plan ID:** PIE_INTAKE_CONTROL_CATALOG_001
**Status:** PLANNING ONLY — NO INGESTION AUTHORIZED
**State:** ENGINEERING_OBSERVER_STATE

---

## 1. SELECTED ARTIFACT TYPE

```
Type Code: 003
Type Name: CONTROL_CATALOG
Description: Structured security or compliance control definitions with relationships
```

---

## 2. EXPECTED FILE FORMATS

### Primary Format: OSCAL (Open Security Controls Assessment Language)

| Format | Extension | MIME Type | Priority |
|--------|-----------|-----------|----------|
| OSCAL JSON | `.json` | `application/json` | PRIMARY |
| OSCAL XML | `.xml` | `application/xml` | SECONDARY |
| NIST Excel | `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | TERTIARY |

### Why OSCAL

OSCAL is the machine-readable standard developed by NIST for security controls:
- Structured hierarchy (Family → Control → Enhancement)
- Explicit cross-references between controls
- Version metadata embedded
- Official government format

### Format Requirements

| Requirement | Specification |
|-------------|---------------|
| Encoding | UTF-8 |
| Schema Version | OSCAL 1.0.0+ |
| Validation | Must pass OSCAL schema validation |
| Size Limit | 50 MB per file |

---

## 3. MINIMAL VIABLE CORPUS

### Recommended Pilot Corpus: NIST SP 800-53 Rev 5

| Artifact | Source | Size | Control Count |
|----------|--------|------|---------------|
| SP 800-53 Rev 5 Catalog | csrc.nist.gov | ~8 MB (JSON) | 1,189 controls |
| SP 800-53A Rev 5 Assessment | csrc.nist.gov | ~12 MB (JSON) | Assessment procedures |
| SP 800-53B Baselines | csrc.nist.gov | ~2 MB (JSON) | LOW/MOD/HIGH mappings |

### Minimal Viable Size

```
Minimum: 1 catalog (SP 800-53 Rev 5)
  - 20 control families
  - 1,189 controls + enhancements
  - Cross-references between controls

Recommended: 3 artifacts (catalog + assessment + baselines)
  - Enables control-to-assessment mapping
  - Enables baseline impact analysis
```

### Corpus Boundaries

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Maximum artifacts | 10 | Bounded analysis scope |
| Maximum total size | 100 MB | Memory constraints |
| Maximum control count | 5,000 | Query performance |
| Single framework per batch | YES | Avoid cross-framework confusion |

---

## 4. VALIDATION STEPS PRIOR TO ACCEPTANCE

### Step 1: Metadata Completeness Check

```
REQUIRED FIELDS:
  □ artifact_id — unique identifier present
  □ artifact_type — equals "CONTROL_CATALOG"
  □ framework — framework name specified
  □ framework_version — version specified
  □ source_url — official source URL
  □ retrieved_at — retrieval timestamp
  □ sha256_hash — hash present
  □ authority — issuing authority specified
  □ authority_level — valid enum value
  □ publication_date — date specified
  □ control_count — integer > 0

FAILURE: Any missing field → REJECT_METADATA_INCOMPLETE
```

### Step 2: Source URL Verification

```
OFFICIAL SOURCES WHITELIST:
  □ csrc.nist.gov — NIST publications
  □ nvd.nist.gov — NIST NVD
  □ iso.org — ISO standards
  □ pcisecuritystandards.org — PCI DSS
  □ hitrust.com — HITRUST CSF
  □ aicpa.org — SOC 2

VERIFICATION:
  □ URL matches whitelist domain
  □ URL uses HTTPS
  □ URL returns HTTP 200

FAILURE: Non-whitelisted source → REJECT_UNOFFICIAL_SOURCE
```

### Step 3: Hash Integrity Verification

```
PROCESS:
  1. Compute SHA-256 of artifact content
  2. Compare against declared sha256_hash
  3. Log both hashes for audit

FAILURE: Hash mismatch → REJECT_INTEGRITY_FAIL
```

### Step 4: Schema Validation

```
OSCAL JSON:
  □ Valid JSON syntax
  □ Passes OSCAL 1.0.0 JSON Schema
  □ Contains required OSCAL elements:
    - catalog or profile root element
    - metadata section
    - controls or groups

OSCAL XML:
  □ Well-formed XML
  □ Passes OSCAL 1.0.0 XSD
  □ Namespace declarations correct

FAILURE: Schema validation error → REJECT_SCHEMA_INVALID
```

### Step 5: Content Sanity Check (No Analysis)

```
STRUCTURAL CHECKS ONLY:
  □ control_count matches actual control count in file
  □ No circular references in control hierarchy
  □ All cross-references resolve to existing controls
  □ No duplicate control IDs

FAILURE: Structural inconsistency → REJECT_STRUCTURE_INVALID
```

### Step 6: Provenance Chain Check

```
IF supersedes field is present:
  □ Referenced artifact exists in corpus OR
  □ Referenced artifact marked as EXTERNAL_REFERENCE

IF framework_version indicates revision:
  □ Previous version documented in provenance chain

FAILURE: Broken provenance → REJECT_PROVENANCE_INCOMPLETE
```

### Validation Flow

```
┌─────────────────────────────────────────────────────────┐
│           CONTROL_CATALOG VALIDATION FLOW               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Artifact Submitted]                                    │
│         │                                                │
│         ▼                                                │
│  Step 1: Metadata ──FAIL──► REJECT_METADATA_INCOMPLETE  │
│         │ PASS                                           │
│         ▼                                                │
│  Step 2: Source URL ──FAIL──► REJECT_UNOFFICIAL_SOURCE  │
│         │ PASS                                           │
│         ▼                                                │
│  Step 3: Hash ──FAIL──► REJECT_INTEGRITY_FAIL           │
│         │ PASS                                           │
│         ▼                                                │
│  Step 4: Schema ──FAIL──► REJECT_SCHEMA_INVALID         │
│         │ PASS                                           │
│         ▼                                                │
│  Step 5: Structure ──FAIL──► REJECT_STRUCTURE_INVALID   │
│         │ PASS                                           │
│         ▼                                                │
│  Step 6: Provenance ──FAIL──► REJECT_PROVENANCE_INCOMPLETE│
│         │ PASS                                           │
│         ▼                                                │
│     [ACCEPTED FOR INGESTION]                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 5. QUESTIONS PIE CAN ANSWER ONCE INGESTED

### Control Dependency Analysis

| Question | Query Type | Expected Output |
|----------|------------|-----------------|
| "Which controls have circular dependencies?" | Cycle detection | List of control cycles |
| "Which controls depend on more than 5 other controls?" | Dependency count | High-dependency controls |
| "Which controls are depended upon by the most others?" | Reverse dependency | Critical control list |
| "Which controls reference controls that don't exist?" | Broken reference | Orphan references |

### Authority Structure Analysis

| Question | Query Type | Expected Output |
|----------|------------|-----------------|
| "Where is control authority implicit but undocumented?" | Gap analysis | Controls without clear ownership |
| "Which controls span multiple responsibility domains?" | Boundary analysis | Cross-domain controls |
| "Which control families have no explicit hierarchy?" | Structure analysis | Flat control families |

### Baseline Impact Analysis

| Question | Query Type | Expected Output |
|----------|------------|-----------------|
| "Which controls differ between LOW and MODERATE baselines?" | Diff analysis | Baseline deltas |
| "Which controls are in HIGH but not in MODERATE?" | Subset analysis | HIGH-only controls |
| "Which baseline assumptions would break under framework version skew?" | Version analysis | Unstable baselines |

### Cross-Reference Analysis

| Question | Query Type | Expected Output |
|----------|------------|-----------------|
| "Which controls reference deprecated controls?" | Deprecation check | Stale references |
| "Which control relationships are bidirectional?" | Symmetry check | Mutual dependencies |
| "Which controls have no incoming or outgoing references?" | Isolation check | Orphan controls |

### Framework Evolution Analysis

| Question | Query Type | Expected Output |
|----------|------------|-----------------|
| "Which controls were added in Rev 5 vs Rev 4?" | Version diff | New controls |
| "Which controls were removed or deprecated?" | Removal analysis | Removed controls |
| "Which control IDs changed between versions?" | ID mapping | Renumbered controls |

---

## 6. EXPLICIT REFUSAL CONDITIONS

### Automatic Rejection

| Condition | Rejection Code | Response |
|-----------|----------------|----------|
| Missing artifact_id | `REJECT_NO_ID` | "REFUSED: artifact_id required" |
| Missing artifact_type | `REJECT_NO_TYPE` | "REFUSED: artifact_type required" |
| artifact_type ≠ CONTROL_CATALOG | `REJECT_TYPE_MISMATCH` | "REFUSED: Expected CONTROL_CATALOG, got {type}" |
| Missing sha256_hash | `REJECT_NO_HASH` | "REFUSED: sha256_hash required for integrity" |
| Hash verification failed | `REJECT_INTEGRITY_FAIL` | "REFUSED: Hash mismatch — content integrity compromised" |
| Non-whitelisted source | `REJECT_UNOFFICIAL_SOURCE` | "REFUSED: Source {url} not in approved list" |
| Schema validation failed | `REJECT_SCHEMA_INVALID` | "REFUSED: OSCAL schema validation failed at {path}" |
| Missing authority | `REJECT_NO_AUTHORITY` | "REFUSED: Issuing authority required" |
| Missing framework_version | `REJECT_NO_VERSION` | "REFUSED: Framework version required" |
| Missing publication_date | `REJECT_NO_PUB_DATE` | "REFUSED: Publication date required for provenance" |
| control_count = 0 | `REJECT_EMPTY_CATALOG` | "REFUSED: Empty catalog provides no analysis value" |
| Circular control references | `REJECT_STRUCTURE_INVALID` | "REFUSED: Circular reference detected: {cycle}" |

### Conditional Rejection

| Condition | Rejection Code | Override |
|-----------|----------------|----------|
| Framework > 5 years old | `REJECT_STALE` | `legacy_override: true` in metadata |
| Corpus size > 100 MB | `REJECT_SIZE_EXCEEDED` | Commander approval |
| Control count > 5,000 | `REJECT_SCOPE_EXCEEDED` | Commander approval |
| Non-OSCAL format | `REJECT_FORMAT_DEPRECATED` | `format_override: true` + manual parser |

### Query Refusals (Post-Ingestion)

| Query Condition | Response |
|-----------------|----------|
| Query references control not in corpus | "REFUSED: Control {id} not in loaded corpus" |
| Query requires cross-framework comparison but only one framework loaded | "REFUSED: Cross-framework query requires multiple frameworks" |
| Query requires version comparison but only one version loaded | "REFUSED: Version diff requires multiple versions" |

---

## 7. INGESTION READINESS CHECKLIST

### Before Requesting Commander Authorization

- [ ] Artifacts identified and URLs documented
- [ ] Expected hashes obtained from official source
- [ ] OSCAL schema validator tested
- [ ] Metadata template prepared
- [ ] Validation pipeline tested with sample
- [ ] Rejection handling tested
- [ ] Query templates prepared
- [ ] Rollback procedure documented

### Commander Authorization Required For

- [ ] Download of artifacts from official sources
- [ ] Execution of validation pipeline
- [ ] Loading into PIE corpus
- [ ] Enabling query interface

---

## 8. STAGING TIMELINE

| Phase | Activity | Status |
|-------|----------|--------|
| Phase 0 | Plan created | ✓ COMPLETE |
| Phase 1 | Validation pipeline built | PENDING |
| Phase 2 | Sample artifact tested | PENDING |
| Phase 3 | Commander authorization | PENDING |
| Phase 4 | Artifact download | BLOCKED |
| Phase 5 | Validation execution | BLOCKED |
| Phase 6 | Corpus loading | BLOCKED |
| Phase 7 | Query enablement | BLOCKED |

---

**PIE: Planning complete. No ingestion performed. Awaiting authorization.**

**State:** ENGINEERING_OBSERVER_STATE
**Artifacts Downloaded:** 0
**Artifacts Ingested:** 0
